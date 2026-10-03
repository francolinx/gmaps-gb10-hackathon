"""Build a ui_scaffold timeline JSON from an AGENT run (venue code, Oct 3). Runs on the host after the run.

Sources:
  * ~/gmaps_venue/log/mcp_calls_<run>.jsonl: what the agent's tool calls returned (events, ledger warnings, look-ahead, alerts)
  * ~/gmaps_venue/log/agent_turns_<run>.jsonl: per-turn wall time and model/provider trace
  * the replay feed rule (received_at <= t) for DISPLAY positions only
The look-ahead shown at time t is the latest result the agent itself requested with as_of <= t; nothing is recomputed here.

  python3 venue/build_timeline.py <run_id> --episode SIM_E1_CROSS_DURING_ROLLOUT --input-mode "..." --out ui_scaffold/samples/agent_live.json
"""
import argparse, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'lib'))
from gmaps_core.sim.simmap import SIM_MAP          # noqa: E402
from gmaps_core.sim.predict import MODEL           # noqa: E402

LOG = Path.home() / 'gmaps_venue' / 'log'


def main():
    a = argparse.ArgumentParser()
    a.add_argument('run_id'); a.add_argument('--episode', required=True); a.add_argument('--input-mode', required=True)
    a.add_argument('--out', required=True); a.add_argument('--t-end', type=int)
    args = a.parse_args()
    calls = [json.loads(l) for l in open(LOG / f'mcp_calls_{args.run_id}.jsonl')]
    turns = [json.loads(l) for l in open(LOG / f'agent_turns_{args.run_id}.jsonl')]
    tr = json.loads((REPO / 'episodes' / f'{args.episode}.transcript.json').read_text())
    ob = json.loads((REPO / 'episodes' / f'{args.episode}.obs.json').read_text())

    parsed = {r['result']['event_id']: r['result'] for r in calls if r['tool'] == 'parse_transmission' and r['ok']}
    transcript, warnings, lookaheads, alerts = [], {}, [], []
    for r in calls:
        if not r['ok']:
            continue
        res = r['result']
        if r['tool'] == 'ledger_ingest':
            ev = parsed[res['event_id']]
            t = ev['event_time']
            transcript.append({'t': t, 'freq': 'tower', 'text': ev['raw_text'], 'speech_act': res['speech_act_resolved'],
                               'kind': res['kind'], 'callsigns': ev['actor_candidates'], 'event_id': res['event_id'],
                               'source_id': ev['source_id'], 'parse_path': ev['parse_path']})
            for w in res['new_warnings']:
                warnings[w['warning_id']] = dict(w)
            for wid in res['cleared_warnings']:
                if wid in warnings:
                    warnings[wid].update(status='cleared', cleared_at=t, cleared_by=res['event_id'])
        elif r['tool'] == 'lookahead' and 'candidates' in res:
            lookaheads.append(res)
        elif r['tool'] == 'lookahead':
            lookaheads.append({'as_of': res['as_of'], 'model': MODEL['version'], 'candidates': [], 'actors': {},
                               'unavailable': [{'track': 'all', 'reason': res.get('reason', 'prediction unavailable')}],
                               'assumptions': [res.get('note', '')]})
        elif r['tool'] == 'post_alert':
            alerts.append({'warning_id': res['warning_id'], 'status': res['status'], 'message_id': res.get('message_id'), 'iso': r['iso'],
                           'lookahead_source': res.get('lookahead_source')})
            if res.get('lookahead_used') and 'candidates' in res['lookahead_used']:
                lookaheads.append(res['lookahead_used'])
    transcript.sort(key=lambda x: x['t'])
    lookaheads.sort(key=lambda x: x['as_of'])

    t_end = args.t_end or int(max([e['t'] for e in tr['events']] + [0])) + 50
    none_yet = {'as_of': None, 'model': MODEL['version'], 'candidates': [], 'actors': {}, 'unavailable': [],
                'assumptions': ['No look-ahead requested by the agent yet.']}
    frames = []
    for t in range(0, t_end + 1):
        la = none_yet
        for x in lookaheads:
            if x['as_of'] <= t:
                la = x
        pos = {}
        for tid, m in ob['tracks'].items():
            seen = [p for p in ob['packets'] if p['track_id'] == tid and p['received_at'] <= t]
            if seen:
                p = seen[-1]
                pos[tid] = {'x': p['position']['x'], 'y': p['position']['y'], 'observed_at': p['observed_at'],
                            'age_s': round(t - p['observed_at'], 1), 'callsign': m['callsign'], 'class': m['class']}
        frames.append({'t': t, 'positions': pos, 'combined': la, 'lookahead_as_of': la['as_of']})

    turn_rows = []
    for x in turns:
        so = x['stdout']
        prov = re.findall(r'"winnerProvider": "(.*?)"', so)
        model = re.findall(r'"winnerModel": "(.*?)"', so)
        turn_rows.append({'t': x['t'], 'wall_s': x['wall_s'], 'rc': x['rc'], 'provider': prov[-1] if prov else None,
                          'model': model[-1] if model else None, 'source_id': x['source_id'],
                          'input_text': x.get('input_text'), 'asr_s': x.get('asr_s')})
    ep = {k: v for k, v in tr.items() if k != 'events'}
    ep['title'] = f"{tr['title']} - agent run {args.run_id} - input: {args.input_mode}"
    out = {'episode': ep, 'transcript': transcript, 'frames': frames, 'map': SIM_MAP, 'model': MODEL,
           'ledger': {'warnings': list(warnings.values())},
           'agent_run': {'run_id': args.run_id, 'input_mode': args.input_mode, 'alerts': alerts, 'turns': turn_rows,
                         'route': 'OpenClaw agent gmaps -> Qwen3.6 via inference.local -> gmaps MCP (unmanaged route over local-inference egress rule)',
                         'look_ahead_source': 'agent-requested lookahead tool results only; positions = received simulated packets (display)'}}
    Path(args.out).write_text(json.dumps(out, default=str))
    print(f"{args.out}: {len(transcript)} transmissions, {len(warnings)} warnings, {len(lookaheads)} look-aheads, "
          f"{len(alerts)} alerts, {len(frames)} frames")


if __name__ == '__main__':
    main()
