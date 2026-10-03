"""Clearance-state ledger and runway-reservation rules (prepared library, stdlib only).

Five state kinds are kept SEPARATE per actor (Eichelberger):
  authorized   - what a controller instruction recorded (never 'what happened')
  acknowledged - what a readback confirmed (or 'unknown' / 'discrepant' / 'not_heard')
  reported     - what a pilot/vehicle said about itself
  inferred     - what this engine derived (always labelled, e.g. 'exit instruction issued')
  observed     - what an independent surveillance/motion source said (never from voice)

Runways are reserved resources. A reservation is created when an authorization is RECORDED and is
released only by a recorded release event (go-around, crossing complete, takeoff/landing reported or
observed complete, exit instruction). A stop/cancel does NOT release a reservation until acknowledged.

A fired rule means: at time t the ledger held two authorizations that need the same protected runway
(or intersecting runways). It does not mean a collision would have happened, and the ledger never
claims it would have prevented one.

Rule IDs and citations follow data/specs/compat_matrix.json (JO 7110.65BB, fetched Oct 2, 2026).
"""
import itertools

_wid = itertools.count(1)
_rid = itertools.count(1)
RESERVATION_FOR = {'LANDING_CLEARANCE': 'LANDING', 'TAKEOFF_CLEARANCE': 'TAKEOFF', 'LUAW': 'LUAW', 'CROSS': 'CROSSING'}
CITE = {
    'R1': '3-1-3; 3-7-2', 'R2': '3-1-3; 3-9-10', 'R3': '3-9-6; 3-10-3', 'R4': '3-9 intersecting runway operations; 3-10-4',
    'R5': '3-9-4; 3-10-5', 'R6': '3-7-2', 'R7': '3-7-2 (read back hold instructions)', 'R8': '3-1-3', 'R9': '3-9-4',
    'R10': '3-1-3; 3-10-5', 'R11': '3-7-2', 'R13': 'stop/cancel acknowledgement (engine rule)'}
NAME = {
    'R1': 'crossing vs active landing', 'R2': 'crossing vs active takeoff', 'R3': 'takeoff vs landing, same runway',
    'R4': 'takeoff vs landing, intersecting runways', 'R5': 'line up and wait vs landing, same runway',
    'R6': 'route word crosses a runway with no hold-short or crossing clearance', 'R7': 'runway hold-short not read back',
    'R8': 'crossing not closed out', 'R9': 'line up and wait timer', 'R10': 'occupied runway vs landing or takeoff',
    'R11': 'two crossings at the same point', 'R13': 'stop/cancel unacknowledged'}
TIMERS = {'R7': 15, 'R8': 90, 'R9': 90, 'R13': 10}
STATE_KINDS = ('authorized', 'acknowledged', 'reported', 'inferred', 'observed')


def hold_text(h):
    if not h:
        return ''
    where = f"runway {h['runway']}" if h.get('runway') else (h.get('taxiway') or '?')
    return 'hold short of ' + where + (f" at {h['at']}" if h.get('at') else '') + (f" on runway {h['on_runway']}" if h.get('on_runway') else '')


def describe(ev):
    parts = [ev['kind'].replace('_', ' ').lower()]
    if ev.get('runway'):
        parts.append('rwy ' + ev['runway'])
    if ev.get('route'):
        parts.append('via ' + '-'.join(ev['route']))
    if ev.get('crossing_at'):
        parts.append('at ' + ev['crossing_at'])
    for h in ev.get('hold_constraints') or []:
        parts.append(hold_text(h))
    return ', '.join(parts)


class Ledger:
    def __init__(self, airport, readback_window_s=30):
        self.ap = airport
        self.inter = airport.intersecting_runways()
        self.window = readback_window_s
        self.events, self.reservations, self.warnings, self.notes = [], [], [], []
        self.actors = {}
        self.pending = []          # instructions awaiting readback
        self.timers = []           # (due_t, rule, payload)
        self.last_addressed = None
        self.last_speaker = None
        self.now = None

    # ------------------------------------------------------------------ helpers
    def _actor(self, cs):
        if cs not in self.actors:
            self.actors[cs] = {k: [] for k in STATE_KINDS}
        return self.actors[cs]

    def _state(self, cs, kind, value, ev, t):
        rec = {'value': value, 't': t, 'event_id': ev['event_id'] if ev else None}
        self._actor(cs)[kind].append(rec)
        return rec

    def _resolve_callsigns(self, ev):
        out = []
        for c in ev['actor_candidates']:
            if c.startswith('?'):
                tail = c[1:]
                known = [k for k in reversed(list(self.actors)) if k.endswith(tail)]
                if known:
                    out.append(known[0])
                    self.notes.append({'t': ev['event_time'], 'event_id': ev['event_id'],
                                       'note': f'abbreviated callsign {tail} resolved to {known[0]} (most recent match; heuristic)'})
                else:
                    out.append(c)
            else:
                out.append(c)
        return out

    def _physical(self, rwy):
        ends = self.ap.runway_end_candidates(rwy) if rwy else []
        phys = sorted({self.ap.physical_runway(e) for e in ends})
        return ends, phys

    def _active(self, **kw):
        return [r for r in self.reservations if r['status'] != 'released' and all(r.get(k) == v for k, v in kw.items())]

    def _snapshot(self, cs):
        a = self.actors.get(cs, {k: [] for k in STATE_KINDS})
        return {k: (a[k][-1]['value'] if a[k] else None) for k in STATE_KINDS}

    def _warn(self, rule, severity, t, runway, a, b, explain, clears, extra=None):
        w = {'warning_id': f'w{next(_wid):04d}', 'rule_id': rule, 'name': NAME[rule], 'severity': severity, 'runway': runway,
             't_fired': t, 'status': 'open', 'cleared_at': None, 'cleared_by': None,
             'authorization_a': a, 'authorization_b': b,
             'state_snapshot': {x['callsign']: self._snapshot(x['callsign']) for x in (a, b) if x and x.get('callsign')},
             'explain': explain, 'what_would_clear_it': clears, 'cite': 'JO 7110.65BB ' + CITE[rule],
             'claim_limit': 'Two recorded authorizations / an open obligation at time t. Not a collision prediction.'}
        if extra:
            w.update(extra)
        self.warnings.append(w)
        return w

    def _clear(self, pred, t, by):
        for w in self.warnings:
            if w['status'] == 'open' and pred(w):
                w.update(status='cleared', cleared_at=t, cleared_by=by)

    @staticmethod
    def _ref(r):
        return {'callsign': r['callsign'], 'type': r['type'], 'runway_end': r['runway_end'], 'physical_runway': r['physical'],
                't_issued': r['t'], 'event_id': r['event_id'], 'acknowledged': r['ack']}

    # ------------------------------------------------------------------ reservations
    def _reserve(self, cs, rtype, rwy, ev, t, extra=None):
        ends, phys = self._physical(rwy)
        if not phys:
            self.notes.append({'t': t, 'event_id': ev['event_id'], 'note': f'runway {rwy} not resolved at {self.ap.icao}; no reservation made'})
            return None
        r = {'reservation_id': f'r{next(_rid):04d}', 'callsign': cs, 'type': rtype, 'runway_end': rwy, 'physical': phys[0],
             'physical_candidates': phys, 't': t, 'event_id': ev['event_id'], 'status': 'active', 'ack': 'pending',
             'released_at': None, 'released_by': None, 'advisory': ev.get('traffic_advisory'), 'basis': 'authorized'}
        if extra:
            r.update(extra)
        self.reservations.append(r)
        self._evaluate(r, t)
        if rtype == 'CROSSING':
            self.timers.append((t + TIMERS['R8'], 'R8', r['reservation_id']))
        if rtype == 'LUAW':
            self.timers.append((t + TIMERS['R9'], 'R9', r['reservation_id']))
        return r

    def _release(self, r, t, by):
        r.update(status='released', released_at=t, released_by=by)
        self._clear(lambda w: any(x and x.get('event_id') == r['event_id'] and x.get('callsign') == r['callsign']
                                  for x in (w['authorization_a'], w['authorization_b'])), t, by)

    def _evaluate(self, r, t):
        for o in self._active():
            if o is r or o['callsign'] == r['callsign']:
                continue
            same = o['physical'] == r['physical']
            pair = tuple(sorted((o['physical'], r['physical'])))
            inter = pair in self.inter
            types = {o['type'], r['type']}
            a, b = self._ref(o), self._ref(r)
            if same and types == {'LANDING', 'CROSSING'}:
                sev = 'CAUTION' if (self._of(r, o, 'CROSSING').get('advisory')) else 'CONFLICT'
                land, cross = self._of(r, o, 'LANDING'), self._of(r, o, 'CROSSING')
                self._warn('R1', sev, t, r['physical'], a, b,
                           f"Runway {land['runway_end']} has a recorded landing authorization for {land['callsign']} (t={land['t']}) "
                           f"and a crossing authorization for {cross['callsign']} at {cross.get('at') or '?'} (t={cross['t']}). "
                           f"Both need the {r['physical'].split(':')[-1]} protected area.",
                           f"{cross['callsign']} reports clear of runway, or {land['callsign']} go-around / landing complete")
            elif same and types == {'TAKEOFF', 'CROSSING'}:
                self._warn('R2', 'CONFLICT', t, r['physical'], a, b,
                           f"Takeoff authorization and crossing authorization recorded on the same runway ({r['physical'].split(':')[-1]}).",
                           'crossing complete, or takeoff cancelled and acknowledged')
            elif same and types == {'TAKEOFF', 'LANDING'}:
                tk = self._of(r, o, 'TAKEOFF')
                sev = 'CAUTION' if tk.get('advisory') else 'CONFLICT'
                self._warn('R3', sev, t, r['physical'], a, b,
                           'Takeoff and landing authorizations recorded on the same physical runway.',
                           'one authorization released (go-around, takeoff cancelled, or operation complete)')
            elif inter and types == {'TAKEOFF', 'LANDING'}:
                second = r
                sev = 'ADVISED' if second.get('advisory') else 'CONFLICT'
                node = [n for n in self.ap.nodes.values() if n['kind'] == 'runway_intersection' and set(pair) <= set(n['surface_ids'])]
                self._warn('R4', sev, t, list(pair), a, b,
                           f"Runways {o['runway_end']} and {r['runway_end']} intersect (draft graph node {node[0]['id'] if node else '?'}). "
                           f"A {r['type'].lower()} authorization for {r['callsign']} was recorded at t={r['t']} while a "
                           f"{o['type'].lower()} authorization for {o['callsign']} (t={o['t']}) is still live"
                           + (f"; traffic information was included ('{second['advisory']}')." if second.get('advisory') else '; no traffic information was included in the second clearance.'),
                           f"{o['callsign']} or {r['callsign']} authorization released (go-around, takeoff cancelled and acknowledged, operation complete)",
                           extra={'graph_basis': node[0]['id'] if node else None})
            elif same and types == {'LUAW', 'LANDING'}:
                land = self._of(r, o, 'LANDING')
                adv = (land.get('advisory') or '').upper()
                sev = 'CAUTION' if 'HOLDING' in adv or 'POSITION' in adv else 'CONFLICT'
                self._warn('R5', sev, t, r['physical'], a, b,
                           'Line up and wait and a landing authorization recorded on the same runway.',
                           'takeoff issued and airborne, or landing authorization withdrawn')
            elif same and 'OCCUPYING' in types and types & {'LANDING', 'TAKEOFF'}:
                occ = self._of(r, o, 'OCCUPYING')
                self._warn('R10', 'CONFLICT', t, r['physical'], a, b,
                           f"{occ['callsign']} is recorded as occupying runway {occ['runway_end']} ({occ['basis']}) while a "
                           f"{(r if r is not occ else o)['type'].lower()} authorization is recorded on the same runway.",
                           f"{occ['callsign']} reported/observed clear of the runway")
            elif same and types == {'CROSSING'} and o.get('at') == r.get('at'):
                self._warn('R11', 'CAUTION', t, r['physical'], a, b, 'Two crossing authorizations at the same point.',
                           'first crossing reported complete')

    @staticmethod
    def _of(r, o, typ):
        return r if r['type'] == typ else o

    # ------------------------------------------------------------------ timers
    def tick(self, t):
        self.now = t
        due = [x for x in self.timers if x[0] <= t]
        self.timers = [x for x in self.timers if x[0] > t]
        for due_t, rule, payload in sorted(due, key=lambda x: x[0]):
            if rule in ('R8', 'R9'):
                r = next((x for x in self.reservations if x['reservation_id'] == payload), None)
                if r and r['status'] != 'released':
                    if rule == 'R8':
                        self._warn('R8', 'REMINDER', due_t, r['physical'], self._ref(r), None,
                                   f"Crossing authorization for {r['callsign']} on {r['runway_end']} is {TIMERS['R8']} s old with no "
                                   'crossing-complete / clear-of-runway report. The runway stays reserved.',
                                   'crossing complete reported')
                    else:
                        self._warn('R9', 'REMINDER', due_t, r['physical'], self._ref(r), None,
                                   f"{r['callsign']} has been in line up and wait for {TIMERS['R9']} s with no further instruction.",
                                   'takeoff clearance or further instruction')
            elif rule == 'R7':
                p = payload
                if not p.get('acknowledged'):
                    self._warn('R7', 'CAUTION', due_t, p['physical'], {'callsign': p['callsign'], 'type': 'HOLD_SHORT', 't_issued': p['t'],
                               'event_id': p['event_id'], 'hold': p['hold']}, None,
                               f"No readback naming the runway hold ({p['hold_text']}) was heard from {p['callsign']} within {TIMERS['R7']} s.",
                               'a readback that names the hold')
            elif rule == 'R13':
                r = next((x for x in self.reservations if x['reservation_id'] == payload), None)
                dup = any(w['rule_id'] == 'R13' and w['status'] == 'open' and w['authorization_a'].get('event_id') == (r or {}).get('event_id') for w in self.warnings)
                if dup:
                    for w in self.warnings:
                        if w['rule_id'] == 'R13' and w['status'] == 'open' and w['authorization_a'].get('event_id') == r['event_id']:
                            w.setdefault('repeat_stop_calls_t', []).append(r['cancel_t'])
                elif r and r.get('cancel_status') == 'unacknowledged':
                    self._warn('R13', 'CAUTION', due_t, r['physical'], self._ref(r), None,
                               f"Stop/cancel issued to {r['callsign']} at t={r['cancel_t']}; no acknowledgement heard in {TIMERS['R13']} s. "
                               'The reservation is kept: the engine does not assume the stop took effect.',
                               f"{r['callsign']} acknowledges, or an observed/reported stop")

    # ------------------------------------------------------------------ ingest
    def ingest(self, ev, t=None):
        t = ev['event_time'] if t is None else t
        self.tick(t)
        self.events.append(ev)
        cs_list = list(dict.fromkeys(self._resolve_callsigns(ev)))   # 'Truck 1, stop, Truck 1, stop' -> one actor
        act, kind = ev['speech_act'], ev['kind']
        if act == 'instruction_or_readback':
            act = self._disambiguate(ev, cs_list, t)
            ev['speech_act_resolved'] = act
        if not cs_list and act == 'readback' and self.last_addressed:
            cs_list = [self.last_addressed]
            self.notes.append({'t': t, 'event_id': ev['event_id'], 'note': f'no callsign heard; readback attributed to last addressed {self.last_addressed} (heuristic)'})
        if not cs_list and act == 'instruction' and self.last_speaker and t - self.last_speaker[1] <= 20:
            cs_list = [self.last_speaker[0]]
            self.notes.append({'t': t, 'event_id': ev['event_id'], 'note': f'instruction with no callsign attributed to the last station heard, {cs_list[0]} (heuristic)'})
        if not cs_list and act == 'report' and kind == 'CROSSING_COMPLETE':
            open_x = self._active(type='CROSSING')
            if len(open_x) == 1:
                cs_list = [open_x[0]['callsign']]
                self.notes.append({'t': t, 'event_id': ev['event_id'], 'note': f'crossing complete with no callsign applied to the only open crossing ({cs_list[0]})'})
        if act == 'instruction' and cs_list:
            self.last_addressed = cs_list[-1]
        if act in ('readback', 'report', 'request') and cs_list:
            self.last_speaker = (cs_list[-1], t)
        for cs in cs_list or [None]:
            if cs is None:
                if act != 'unknown':
                    self.notes.append({'t': t, 'event_id': ev['event_id'], 'note': f'{kind} with no attributable callsign; recorded only'})
                continue
            getattr(self, '_on_' + act, self._on_unknown)(cs, ev, t)
        return ev

    def _disambiguate(self, ev, cs_list, t):
        cs = cs_list[-1] if cs_list else self.last_addressed
        for p in reversed(self.pending):
            fam = p['kind'] == ev['kind'] or {p['kind'], ev['kind']} <= {'TAXI', 'HOLD_SHORT'}
            if p['callsign'] == cs and t - p['t'] <= self.window and fam and p.get('acknowledged') not in (True, 'superseded'):
                return 'readback'
        return 'instruction'

    def _on_unknown(self, cs, ev, t):
        if ev['speech_act'] in ('unknown',):
            return

    def _on_request(self, cs, ev, t):
        self._state(cs, 'reported', f"requests {ev['kind'].lower()}" + (f" runway {ev['runway']} at {ev['crossing_at']}" if ev.get('runway') else ''), ev, t)

    def _on_instruction(self, cs, ev, t):
        kind = ev['kind']
        self._state(cs, 'authorized', describe(ev), ev, t)
        if kind in RESERVATION_FOR:
            if kind == 'TAKEOFF_CLEARANCE':
                for r in self._active(callsign=cs, type='LUAW'):
                    self._release(r, t, 'takeoff clearance issued')
            self._reserve(cs, RESERVATION_FOR[kind], ev.get('runway'), ev, t, extra={'at': ev.get('crossing_at')})
            self.pending.append({'callsign': cs, 'kind': kind, 't': t, 'event_id': ev['event_id'], 'runway': ev.get('runway'),
                                 'hold': None, 'crossing_at': ev.get('crossing_at')})
        elif kind in ('TAXI', 'HOLD_SHORT'):
            for r in self._active(callsign=cs, type='OCCUPYING'):
                if not any(h.get('on_runway') for h in ev['hold_constraints']):
                    self._release(r, t, 'exit/taxi instruction issued (inferred clear; not observed)')
                    self._state(cs, 'inferred', f"exit instruction issued; runway {r['runway_end']} assumed vacating (not observed)", ev, t)
            for p in self.pending:
                if p['callsign'] == cs and p['kind'] in ('TAXI', 'HOLD_SHORT') and not p.get('acknowledged'):
                    p['superseded_by'] = ev['event_id']
                    p['acknowledged'] = 'superseded'
                    ev['supersedes_event_id'] = p['event_id']
                    self._clear(lambda w, p=p: w['rule_id'] == 'R7' and w['authorization_a'].get('event_id') == p['event_id'], t, 'superseded by a new instruction')
            for h in ev['hold_constraints']:
                if h.get('on_runway'):
                    self._reserve(cs, 'OCCUPYING', h['on_runway'], ev, t, extra={'basis': 'authorized: hold on runway'})
            pend = {'callsign': cs, 'kind': kind, 't': t, 'event_id': ev['event_id'], 'runway': ev.get('runway'),
                    'route': ev.get('route'), 'hold': (ev['hold_constraints'] or [None])[0]}
            self.pending.append(pend)
            hold = pend['hold'] or {}
            if hold.get('runway'):
                _, phys = self._physical(hold['runway'])
                pend.update(physical=phys[0] if phys else None, hold_text=f"hold short runway {hold['runway']}" + (f" at {hold['at']}" if hold.get('at') else ''))
                self.timers.append((t + TIMERS['R7'], 'R7', pend))
            if kind == 'TAXI' and ev.get('route'):
                self._route_check(cs, ev, t)
        elif kind == 'CANCEL':
            rs = self._active(callsign=cs)
            if not rs:
                self.notes.append({'t': t, 'event_id': ev['event_id'], 'note': f'stop/cancel to {cs}: no recorded reservation for {cs}'})
            for r in rs:
                r.update(cancel_status='unacknowledged', cancel_t=t, status='cancel_unacknowledged')
                self.timers.append((t + TIMERS['R13'], 'R13', r['reservation_id']))
        elif kind == 'GO_AROUND':
            rs = self._active(callsign=cs, type='LANDING')
            if not rs:
                prior = [r for r in self.reservations if r['callsign'] == cs and r['type'] == 'LANDING']
                self.notes.append({'t': t, 'event_id': ev['event_id'], 'note': f'go-around for {cs}: ' +
                                   ('landing authorization already released' if prior else 'no recorded landing authorization (not captured)')})
            for r in rs:
                self._release(r, t, f'go-around instructed to {cs}')
        elif kind == 'FREQ_CHANGE':
            self._state(cs, 'authorized', f"contact {ev.get('normalized_text')}", ev, t)

    def _route_check(self, cs, ev, t):
        rep = self.ap.route_runway_check(ev['route'])
        ev['route_check'] = rep
        held = set()
        for h in ev['hold_constraints']:
            if h.get('runway'):
                held |= set(self._physical(h['runway'])[1])
        crossing_ok = {r['physical'] for r in self._active(callsign=cs, type='CROSSING')}
        for item in rep:
            for x in item['crossings']:
                if x['runway_id'] not in held and x['runway_id'] not in crossing_ok:
                    self._warn('R6', 'CAUTION', t, x['runway_id'], {'callsign': cs, 'type': 'TAXI', 't_issued': t, 'event_id': ev['event_id'],
                               'route': ev['route']}, None,
                               f"Route word {item['word']} meets runway {x['runway_id'].split(':')[-1]} at {x['node_id']} on the review-pending "
                               f"draft graph, and no hold-short or crossing clearance for that runway was recorded. Direction of travel on "
                               f"{item['word']} is not established in v1, so this is a possible crossing, not a traced one.",
                               'hold-short for that runway issued and read back, or crossing clearance',
                               extra={'graph_basis': x['node_id'], 'graph_status': 'draft, expert review pending'})
        unk = [i['word'] for i in rep if i['status'] == 'no_crossing_data_in_draft_graph']
        if unk:
            self.notes.append({'t': t, 'event_id': ev['event_id'],
                               'note': f"route words {', '.join(unk)}: no reviewed runway-crossing data in the draft graph; hold coverage not checkable (unresolved, not 'clear')"})

    def _on_readback(self, cs, ev, t):
        p = next((p for p in reversed(self.pending) if p['callsign'] == cs and t - p['t'] <= self.window
                  and p.get('acknowledged') not in ('superseded',) and (p['kind'] == ev['kind'] or {p['kind'], ev['kind']} <= {'TAXI', 'HOLD_SHORT'})), None)
        if p is None:
            self._state(cs, 'reported', f"readback-like transmission with no matching recorded instruction: {ev['normalized_text']}", ev, t)
            return
        issues = []
        if p.get('runway') and ev.get('runway') and p['runway'] != ev['runway']:
            issues.append(('discrepant_runway', f"instruction runway {p['runway']}, readback runway {ev['runway']}"))
        ph = p.get('hold') or {}
        rh = (ev['hold_constraints'] or [None])[0] or {}
        if ph.get('runway'):
            if not rh:
                issues.append(('hold_not_heard', 'readback clipped before the hold' if ev.get('clipped') else 'readback did not include the hold'))
            elif rh.get('runway') and rh['runway'] != ph['runway']:
                issues.append(('discrepant_hold', f"hold short runway {ph['runway']} instructed, readback says runway {rh['runway']}"))
        if not issues:
            p['acknowledged'] = True
            self._state(cs, 'acknowledged', 'read back: ' + describe(ev), ev, t)
            for r in self.reservations:
                if r['event_id'] == p['event_id'] and r['ack'] == 'pending':
                    r['ack'] = 'acknowledged'
            self._clear(lambda w: w['rule_id'] == 'R7' and w['authorization_a'].get('callsign') == cs, t, f"readback {ev['event_id']} named the hold")
            return
        for code, text in issues:
            self._state(cs, 'acknowledged', f'{code}: {text}', ev, t)
            if code in ('discrepant_hold', 'discrepant_runway'):
                p['acknowledged'] = 'discrepant'
                self._warn('R7', 'CONFLICT', t, p.get('physical'), {'callsign': cs, 'type': p['kind'], 't_issued': p['t'], 'event_id': p['event_id']},
                           {'callsign': cs, 'type': 'READBACK', 't_issued': t, 'event_id': ev['event_id']},
                           f'Readback differs from the recorded instruction: {text}.', 'controller corrects; correct readback heard')
            elif code == 'hold_not_heard' and ph.get('runway'):
                p['acknowledged'] = 'not_heard'
                self._warn('R7', 'CAUTION', t, p.get('physical'), {'callsign': cs, 'type': p['kind'], 't_issued': p['t'], 'event_id': p['event_id'], 'hold': ph},
                           {'callsign': cs, 'type': 'READBACK', 't_issued': t, 'event_id': ev['event_id']},
                           f"{p.get('hold_text', 'runway hold')} not heard in the readback ({text}). Acknowledged state for the hold = UNKNOWN, not 'acknowledged'.",
                           'a readback that names the hold', extra={'parse_confidence_heuristic': ev['uncertainty']['confidence_heuristic']})
        # drop the pending R7 timer for this instruction: the readback was heard, the issue is now explicit
        p['acknowledged'] = p.get('acknowledged') or 'issue'

    def _on_report(self, cs, ev, t):
        kind = ev['kind']
        self._state(cs, 'reported', describe(ev).replace('report ', ''), ev, t)
        if kind == 'REPORT_REJECTED_TAKEOFF':
            for r in self._active(callsign=cs, type='TAKEOFF'):
                self._release(r, t, 'rejected takeoff reported')
            rwy = ev.get('runway') or next((r['runway_end'] for r in reversed(self.reservations) if r['callsign'] == cs and r['type'] == 'TAKEOFF'), None)
            if rwy:
                self._reserve(cs, 'OCCUPYING', rwy, ev, t, extra={'basis': 'reported: rejected takeoff, still on runway'})
        elif kind == 'GO_AROUND':
            for r in self._active(callsign=cs, type='LANDING'):
                self._release(r, t, 'go-around reported')
        elif kind == 'CROSSING_COMPLETE':
            rs = self._active(callsign=cs, type='CROSSING') or ([r for r in self._active(type='CROSSING')] if ev.get('runway') is None else [])
            for r in rs[:1]:
                self._release(r, t, 'crossing complete reported')
        elif kind == 'REPORT_HOLDING_POSITION':
            for r in self.reservations:
                if r['callsign'] == cs and r.get('cancel_status') == 'unacknowledged':
                    r['cancel_status'] = 'acknowledged'
                    self._clear(lambda w: w['rule_id'] == 'R13' and w['authorization_a'].get('callsign') == cs, t, 'stop acknowledged')
            if not any(r['callsign'] == cs for r in self.reservations):
                self.notes.append({'t': t, 'event_id': ev['event_id'], 'note': f'{cs} reports holding position (acknowledges stop)'})

    def observe(self, callsign, text, t, source='surveillance'):
        """Record an independent observation (ADS-B/ASDE-X/simulated track summary). Never derived from voice."""
        self.tick(t)
        self._state(callsign, 'observed', f'{text} [{source}]', None, t)

    # ------------------------------------------------------------------ export
    def export(self):
        return {'airport': self.ap.version, 'events': self.events, 'reservations': self.reservations,
                'warnings': self.warnings, 'notes': self.notes, 'actors': self.actors,
                'claim_limit': 'Recorded authorizations and open obligations only; no prevention claims.'}
