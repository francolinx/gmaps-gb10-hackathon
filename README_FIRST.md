# GMAPS prep kit (Boston Dell × NVIDIA GB10 hackathon, Sat Oct 3 2026)

**Organizer rule, as recorded in our master doc:** "No pre-built agents. Plans, scaffolds, libraries and model/dependency files may be prepared."

This kit therefore contains **only what is allowed to be prepared**:
- tested libraries
- fixtures
- a display scaffold
- documentation

**What is not in the kit:** the competition agent. That means speech recognition feeding Nemotron tool calls through NemoClaw/OpenClaw/OpenShell, which in turn call these libraries, update the display and post to the channel. **You assemble that at the venue.** Make your first commit there `import prepared libraries (built Oct 2–3 before the event)`. If anyone asks, say so plainly.

Ask at check-in if you want extra certainty that bringing these libraries is fine.

## Five-minute start on the GB10

```bash
mkdir -p ~/gmaps && cp -r /media/$USER/GBeast10/GB10_ARSENAL/gmaps/gmaps_prep_kit/. ~/gmaps/ && cd ~/gmaps
```

Copying off the exFAT drive keeps Linux file permissions sane.

```bash
python3 tests/run_all.py
```

Expect `53/53 passed`. If jsonschema is missing, the graph check fails on purpose. Install it in a venv (`python3 -m venv ~/gvenv && ~/gvenv/bin/pip install jsonschema`) and run the tests with `~/gvenv/bin/python`.

```bash
python3 eval/run_eval.py
```

This prints the scores for the three methods (route-only, motion-only, combined) on the six fictional episodes.

```bash
cd ui_scaffold && python3 -m http.server 8765
```

Then open http://localhost:8765 in a browser.

Next steps are in `docs/RUNBOOK_GB10.md` (vLLM + Nemotron + Whisper, in order) and `docs/AGENT_ASSEMBLY_PLAN.md`.

## Map of the kit

| Path | What | Who reads it at runtime |
|---|---|---|
| `lib/gmaps_core/normalize.py`, `parser.py` | Grammar-first parsing of ATC radio text into typed events: runway suffixes, double letters, callsigns. A request is never treated as an authorization. | runtime |
| `lib/gmaps_core/airport.py` | Read-only lookups on the reviewed-pending KLGA/KBOS v1 graphs: identifiers and topology review. No routing. | runtime |
| `lib/gmaps_core/ledger.py` | The five-state ledger (authorized, acknowledged, reported, inferred, observed), runways as reserved resources, and rules R1–R13 with explanations and "clears on" conditions. | runtime |
| `lib/gmaps_core/sim/` | The fictional SIM-1 map, the observation emitter, the intent-aware look-ahead predictor (`predict.py`), and the simulation truth (`truth.py`, used by the eval only). | runtime, except `truth.py` |
| `lib/gmaps_core/adapters.py` | Whisper-from-local-folder, a localhost-only LLM client, the residue JSON schema and tool schemas. **Untested on the GB10.** | runtime |
| `data/airports/` | `klga.graph.json` and `kbos.graph.json` (draft2), the schema, `validate.py`, aliases and sources. | runtime + validation |
| `data/specs/` | `scenarios.json` (LGA/BOS/taxi/clipped), `phraseology_grammar.json`, `compat_matrix.json`, and the OLD `lga_graph.json` (reference only: it wrongly says E crosses 4/22). | fixtures |
| `episodes/` | Fictional episode inputs: `*.transcript.json` (the "radio", for re-voicing) and `*.obs.json` (the "sensor"). | runtime |
| `eval/truth/`, `eval/labels/`, `eval/run_eval.py` | Truth and expected answers. **Only the eval runner reads these.** | eval only |
| `tools/` | Test harnesses: `replay_fixture.py`, `run_sim_episode.py`, `make_episodes.py` (including `--hidden N --seed S` for a blind test). | dev |
| `ui_scaffold/` | Single-file offline display plus sample timelines. | display |
| `tests/run_all.py`, `tests/parse_scan.py` | 53 checks: parser, ledger on all four scenarios in both speaker-hint modes and both text modes, the variants, separation, no-future-leak, and episode regressions. | dev |
| `docs/` | Runbook, agent assembly plan, re-voice script, Rachel's card, demo arc, judge Q&A, what is built. | people |

## Claims discipline (applies to everything you say tomorrow)

- A fired rule means the ledger held two recorded authorizations needing one runway at time t. Nothing more.
- Never say GMAPS "would have prevented LaGuardia". Say "frequency", not "channel".
- Re-voice all audio. Never redistribute VASAviation audio.
- SIM-1 is fictional, and the predictor's numbers are engineering choices, not aviation standards.
- "Prediction unavailable" is never the same as "no conflict".

## Before making any repo public
`data/airports/sources/` contains private project notes: `gmaps_master_reference.txt`, `joe_design_addendum11.txt`, `lga_resources_addendum14.txt` and `notes_from_joe.txt`. Leave them out of a public repo.

Without them, `validate.py` reports "missing source file" errors. That's expected; run the full validation locally. The FAA diagram PDFs are public.
