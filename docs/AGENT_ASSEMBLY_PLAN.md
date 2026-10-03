# Agent assembly plan (build this AT THE VENUE)

The organizer rule as we recorded it: no pre-built agents. This file is a plan, the code here is libraries, and you write the loop today.

## Target loop (about 150 lines of glue)
```
clip arrives (re-voiced WAV, one transmission)
  -> transcribe(wav)                      [adapters.transcribe, Whisper turbo, local]
  -> parse(text, airport, resolver)       [parser.parse, grammar first]
       if speech_act == 'unknown': LocalLLM.parse_residue(text)   [Nemotron, reasoning off, JSON schema]
  -> ledger.ingest(event, t)              [ledger.Ledger]
  -> lookahead: predict(as_of, tracks, intents_from(ledger))      [sim.predict; tracks = simulated obs packets received so far]
  -> new warnings / candidates -> display timeline JSON + post_alert to the approved channel
```

The **agent** part is Nemotron deciding which tool to call next through NemoClaw/OpenClaw. For example:
- "new transmission: parse it; if it changes a runway reservation, run the look-ahead"
- "a warning opened: summarize it with its sources and post it"

Register `adapters.TOOL_SCHEMAS`. Keep the tools bounded; no shell access.

## Order of work (stop each step when its check passes)
1. **ASR on one clip.** Check: the text plus its source interval is printed.
2. **One structured tool call.** Nemotron calls `parse_transmission` on that text and gets the typed event back. Check: it appears in the log.
3. **Ledger plus display.** Feed the six lines of SIM_E1 as clips. Check: R1 CONFLICT at the crossing clearance, visible in the UI.
4. **Look-ahead.** Each clip's time T drives `as_of`. Observations come from `episodes/<id>.obs.json`, only packets with `received_at <= as_of`. Check: a candidate is raised before the simulated encounter, and its assumptions are visible.
5. **Negative and degraded paths:**
   - E2: no overlap from the look-ahead.
   - E3: stop not acknowledged, candidate kept.
   - E4: feed lost, prediction withdrawn.
   - E6: hold-short honoured, no alarm.
6. **Channel.** `post_alert` sends one message per new CONFLICT or look-ahead candidate to the approved Slack/Discord/Telegram channel. Check: the message is visible. Never post raw private data.
7. **Blind test.** Run `make_episodes.py --hidden 6 --seed <chosen live>`. Note that `eval/run_eval.py` scores the prepared **libraries** through the harness `run_sim_episode.run()`, not your agent. To score the agent itself, have it write frames in the same shape (`{'t', 'combined': {'candidates': [...]}}`) and adapt `score()` to read them. Report what you get, including any misses, and say which one you scored.
8. **Record latency.** Log wall-clock from end of clip to warning on screen (p50 and p95 over the clips you ran). Measured numbers only.

## Glue snippets you will need (adapt freely)
```python
import json, sys; sys.path.insert(0, 'lib'); sys.path.insert(0, 'tools')
from gmaps_core.parser import parse
from gmaps_core.ledger import Ledger
from gmaps_core.sim.simmap import SimAirport
from gmaps_core.sim.predict import predict
from run_sim_episode import intents_from        # helper: ledger -> predictor intent context
ap = SimAirport(); led = Ledger(ap)
ob = json.load(open('episodes/SIM_E1_CROSS_DURING_ROLLOUT.obs.json'))
tracks = {tid: dict(m, packets=[p for p in ob['packets'] if p['track_id'] == tid]) for tid, m in ob['tracks'].items()}
by_cs = {m['callsign']: tracks[tid]['packets'] for tid, m in ob['tracks'].items()}
# per clip:
ev = parse(asr_text, 'XSIM', resolver=ap, event_time=t, source={'id': wav_name, 'start_s': t, 'end_s': None})
led.ingest(ev, t)
out = predict(t, tracks, intents_from(led, by_cs, t), 'combined')
```

## Things judges may poke at, and where the answer lives
- **"Is the prediction real?"** It runs from received simulated packets only, and the no-future-leak test proves it. Truth and labels live in `eval/` and the runtime never opens them.
- **"Why not just ASDE-X?"** Surveillance systems already alert on motion. GMAPS adds the instruction layer: who was told what, whether it was read back, and whether motion is consistent with it.
- **"Real airport?"** The LGA and BOS graphs are draft topology for identifier lookup, pending expert review. The look-ahead runs on a fictional map by design.
