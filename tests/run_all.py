"""Run every prepared-library test. stdlib only (validate.py needs jsonschema>=4.18 for the graph checks).

usage: python3 tests/run_all.py
Exit code 0 = all passed. Prints one line per test.
"""
import json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib')); sys.path.insert(0, str(ROOT / 'tools'))
from gmaps_core.parser import parse
from gmaps_core.airport import Airport
from gmaps_core.ledger import Ledger
import replay_fixture as RF
import run_sim_episode as RS

LGA = Airport(ROOT / 'data/airports/klga.graph.json')
BOS = Airport(ROOT / 'data/airports/kbos.graph.json')
results = []


def check(name, cond, detail=''):
    results.append((name, bool(cond), detail))


# ---------------- graphs ----------------
try:
    import jsonschema  # noqa
    r = subprocess.run([sys.executable, 'validate.py', '--self-test'], cwd=ROOT / 'data/airports', capture_output=True, text=True)
    rep = json.loads(r.stdout)
    check('graphs: validate.py --self-test (both airports)', rep['all_checks_passed'], f"{len(rep['self_tests'])} self-tests")
    r2 = subprocess.run([sys.executable, 'bos_extra_tests.py'], cwd=ROOT / 'data/airports', capture_output=True, text=True)
    check('graphs: bos_extra_tests.py', 'ALL True' in r2.stdout)
except ImportError:
    check('graphs: validate.py NOT RUN - jsonschema missing (see RUNBOOK step 1)', False, 'install jsonschema to run graph checks')

# ---------------- parser ----------------
P = lambda txt, ap=LGA, hint=None: parse(txt, ap.icao, speaker_hint=hint, resolver=ap)
e = P('Truck 1 and company, cross 4 at Delta.', hint='ATC')
check('parser: crossing instruction', (e['kind'], e['speech_act'], e['runway'], e['crossing_at'], e['actor_candidates']) == ('CROSS', 'instruction', '04', 'D', ['TRUCK1']))
e = P('Truck 1 and company, LaGuardia Tower, requesting to cross 4 at Delta.')
check('parser: a request is never an authorization', e['speech_act'] == 'request' and e['kind'] == 'CROSS_REQUEST')
e = P('Runway 4, cleared to land, number two, Jazz 646.', hint='ATC')
check('parser: landing clearance with sequence', (e['kind'], e['runway'], e['sequence']) == ('LANDING_CLEARANCE', '04', '2'))
e = P('United 2384, runway 13, taxi via November, Alpha, Echo, hold short runway 4.', hint='ATC')
check('parser: 3-7-2 taxi with runway hold', e['route'] == ['N', 'A', 'E'] and e['hold_constraints'] == [{'runway': '04'}])
e = P('alpha alpha', hint='ATC')
e2 = parse('Cobalt 41 taxi via alpha alpha, delta, hold short runway four', 'KLGA', speaker_hint='ATC', resolver=LGA)
check('parser: double letter preserved (AA)', e2['route'] == ['AA', 'D'])
e = parse('American 3161, runway two seven, cleared for takeoff.', 'KBOS', speaker_hint='ATC', resolver=BOS)
check('parser: BOS runway 27 normalisation', e['runway'] == '27' and e['runway_end_candidates'] == ['KBOS:END:27'])
e = parse('Delta 2351, runway three three left, cleared to land.', 'KBOS', speaker_hint='ATC', resolver=BOS)
check('parser: BOS 33L (airline Delta is a callsign, not taxiway D)', e['runway'] == '33L' and e['actor_candidates'] == ['DAL2351'] and e['runway_end_candidates'] == ['KBOS:END:33L'])
e = parse('Delta 2351, runway 33, cleared to land.', 'KBOS', speaker_hint='ATC', resolver=BOS)
check('parser: missing suffix stays ambiguous (33L+33R)', e['runway_end_candidates'] == ['KBOS:END:33L', 'KBOS:END:33R'])
e = parse('Tradewind 82, taxi via delta one', 'KBOS', speaker_hint='ATC', resolver=BOS)
check('parser: D1 vs D (BOS)', e['route'] == ['D1'])
e = parse('Tradewind 82, taxi via delta one', 'KLGA', speaker_hint='ATC', resolver=LGA)
check('parser: D1 not in LGA inventory -> unresolved, not corrected', any('D1' in u for u in e['uncertainty']['unresolved']))
e = P('Delta 263, go around, runway heading, 2000.', hint='ATC')
check('parser: altitude 2000 is not a callsign', e['actor_candidates'] == ['DAL263'])
e = P('make the right turn at Lima and a left turn on Bravo', hint='ATC')
check('parser: article "a" is not taxiway A', e['route'] == ['L', 'B'])
e = P('Runway 13, Alpha, Delta, ho— [clipped]', hint='PILOT')
check('parser: clipped readback flagged, hold not invented', e['clipped'] and e['hold_constraints'] == [])

# ---------------- ledger on fixtures ----------------
def rules(sid, **kw):
    led, _ = RF.run(RF.load_scenarios()[sid], **kw)
    return led
for hints in (True, False):
    for text in ('clean', 'raw'):
        tag = f"hints={hints},text={text}"
        L = rules('LGA_2026-03-22', hints=hints, text=text)
        r1 = [w for w in L.warnings if w['rule_id'] == 'R1']
        check(f'ledger LGA: R1 CONFLICT at t=40 ({tag})', r1 and r1[0]['t_fired'] == 40 and r1[0]['severity'] == 'CONFLICT')
        check(f'ledger LGA: no flag on t=-577 takeoff 13 negative case ({tag})', not [w for w in L.warnings if w['t_fired'] < 0])
        check(f'ledger LGA: stop to TRUCK1 not assumed effective (R13) ({tag})', any(w['rule_id'] == 'R13' and w['authorization_a']['callsign'] == 'TRUCK1' for w in L.warnings))
        B = rules('BOS_2026-06-20', hints=hints, text=text)
        r4 = [w for w in B.warnings if w['rule_id'] == 'R4']
        check(f'ledger BOS: R4 CONFLICT at t=82, cleared at go-around t=144 ({tag})', r4 and r4[0]['t_fired'] == 82 and r4[0]['severity'] == 'CONFLICT' and r4[0]['cleared_at'] == 144)
        check(f'ledger BOS: LUAW at t=0 to takeoff at t=82 < 90 s, no R9 ({tag})', not [w for w in B.warnings if w['rule_id'] == 'R9'])
        C = rules('CLIPPED_READBACK_FICTIONAL', hints=hints, text=text)
        r7 = [w for w in C.warnings if w['rule_id'] == 'R7']
        check(f'ledger CLIPPED: hold not heard -> CAUTION, cleared by full readback ({tag})', r7 and r7[0]['severity'] == 'CAUTION' and r7[0]['status'] == 'cleared')
        T = rules('TAXI_EXERCISE_LGA_N_A_E', hints=hints, text=text)
        check(f'ledger TAXI: no warnings; N/A/E coverage reported unresolved ({tag})', not T.warnings and any('unresolved' in n['note'] for n in T.notes))


def variant(lines, ap=LGA):
    led = Ledger(ap)
    for t, hint, txt in lines:
        led.ingest(parse(txt, ap.icao, speaker_hint=hint, resolver=ap, event_time=t), t)
    led.tick(lines[-1][0] + 120)
    return led
V = variant([(0, 'ATC', 'Cobalt 41, runway 13, taxi via Alpha Alpha, Delta.'), (5, 'PILOT', 'Runway 13, Alpha Alpha, Delta, Cobalt 41.')])
check('ledger variant A: route word D meets 04/22 with no hold -> R6 (possible crossing, draft graph)', any(w['rule_id'] == 'R6' and w['graph_basis'] == 'KLGA:N:D_RWY04-22' for w in V.warnings))
V = variant([(0, 'ATC', 'Cobalt 41, runway 13, taxi via Alpha, Delta, hold short runway 4.'), (5, 'PILOT', 'Runway 13, Alpha, Delta, hold short runway 13, Cobalt 41.')])
check('ledger variant B: discrepant hold readback -> R7 CONFLICT', any(w['rule_id'] == 'R7' and w['severity'] == 'CONFLICT' for w in V.warnings))
V = variant([(0, 'ATC', 'Cobalt 41, cross runway 4 at Delta.'), (4, 'PILOT', 'Crossing runway 4 at Delta, Cobalt 41.')])
check('ledger variant C: crossing not closed out -> R8 REMINDER at +90 s', any(w['rule_id'] == 'R8' and w['t_fired'] == 90 for w in V.warnings))
V = variant([(0, 'ATC', 'Delta 520, runway 22, cleared for takeoff.'), (5, 'ATC', 'Jazz 646, runway 4, cleared to land.')])
check('ledger: 04 and 22 are the same physical runway (R3)', any(w['rule_id'] == 'R3' for w in V.warnings))

# ---------------- separation and no-future-leak ----------------
src = {p.name: p.read_text() for p in (ROOT / 'lib/gmaps_core/sim').glob('*.py')}
check('separation: predictor never imports truth', 'truth' not in re.sub(r'""".*?"""', '', src['predict.py'], flags=re.S))
check('separation: runtime harness never opens eval/', 'eval/' not in re.sub(r'""".*?"""', '', (ROOT / 'tools/run_sim_episode.py').read_text(), flags=re.S))
from gmaps_core.sim.predict import predict
ob = json.loads((ROOT / 'episodes/SIM_E1_CROSS_DURING_ROLLOUT.obs.json').read_text())
tracks_full = {tid: dict(meta, packets=[p for p in ob['packets'] if p['track_id'] == tid]) for tid, meta in ob['tracks'].items()}
tracks_cut = {tid: dict(tr, packets=[p for p in tr['packets'] if p['received_at'] <= 40]) for tid, tr in tracks_full.items()}
it = {'SIM212': {'authorized': ['LANDING'], 'surface': 'XSIM:RWY:18-36', 'direction': '36', 'hold': None},
      'RESCUE7': {'authorized': ['CROSSING'], 'surface': 'XSIM:TWY:K', 'direction': 'north', 'hold': None}}
a, b = predict(40, tracks_full, it), predict(40, tracks_cut, it)
check('no-future-leak: prediction at t=40 identical with or without later packets', json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True))

# ---------------- episodes (regression on the six named fictional episodes) ----------------
sys.path.insert(0, str(ROOT / 'eval'))
import run_eval as RE
named = ['SIM_E1_CROSS_DURING_ROLLOUT', 'SIM_E2_SAME_PATHS_LATER', 'SIM_E3_STOP_NOT_OBSERVED', 'SIM_E4_FEED_LOSS', 'SIM_E5_HOLD_NOT_SLOWING', 'SIM_E6_HOLD_OK']
rows = {e: RE.score(e) for e in named}
check('episodes: combined has no MISS/FP/LATE on the six named episodes', all(r['combined']['outcome'] in ('TP', 'TN') for r in rows.values()),
      json.dumps({e[4:7]: r['combined']['outcome'] for e, r in rows.items()}))
check('episodes: E4 feed loss withdraws the vehicle prediction', rows['SIM_E4_FEED_LOSS']['combined_withdrawn_ticks'] > 0)
res = RS.run('SIM_E3_STOP_NOT_OBSERVED')
check('episodes: E3 candidate persists after the unacknowledged stop', any(c['raised'] for c in res['frames'][45]['combined']['candidates']))

ok = all(r[1] for r in results)
for n, passed, d in results:
    print(('PASS ' if passed else 'FAIL ') + n + (f'  [{d}]' if d else ''))
print(f"\n{sum(r[1] for r in results)}/{len(results)} passed")
sys.exit(0 if ok else 1)
