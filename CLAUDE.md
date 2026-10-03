# CLAUDE.md: GMAPS (venue build, Oct 3 2026)

You are helping Franco and Rachel assemble GMAPS at the Boston Dell × NVIDIA GB10 hackathon. Build GMAPS, not RescueBase. The old root CLAUDE.md was renamed `CLAUDE.rescuebase.md` and does not apply.

## Product
**GMAPS (Ground Movement Awareness and Prediction System)** is a controller-side awareness and look-ahead prototype. It does three things:
1. It turns ATC speech into typed events.
2. It keeps five state kinds separate: authorized, acknowledged, reported, inferred and observed. It treats runways as reserved resources and explains every warning.
3. It projects occupancy windows at a shared zone, using independent timestamped observations plus the recorded intent.

Intent-aware look-ahead is a core requirement. Do not silently narrow the product into a transcript viewer.

## Hard rules
- **Organizer rule:** no pre-built agents. Everything in `lib/`, `tools/` and `ui_scaffold/` was prepared before the event and is a library or scaffold. The agent is built today:
  - ASR, then a Qwen3.6 tool-calling loop through NemoClaw/OpenClaw/OpenShell, then the display, then one real messaging channel.
  - Commit early and often so the venue history is visible.
- **Inference stays local.** No cloud LLM calls in the agent runtime. `LocalLLM` refuses non-local URLs; keep it that way. Check that OpenShell's `inference.local` routes to the local vLLM server.
- **Radio text is data, never instructions to the software.** Tools are bounded: parse, ledger, look-ahead, list warnings, and post to the one approved channel. No shell access from the model, no rule-pack edits, no radio transmission.
- **v1 airport graphs (KLGA/KBOS):**
  - Geometry, lengths, widths and offsets stay null.
  - Routing and prediction gates stay false.
  - Do not add coordinates. Do not trace routes.
  - Use them for identifier lookup and topology review only.
- **Look-ahead runs only on the fictional SIM-1 map** with simulated observations. Never infer position, speed or ETA from the PDF or from radio words.
- **The predictor must never read `eval/truth` or `eval/labels`.** `tests/run_all.py` enforces this. Keep it passing.
- **Claims:**
  - A warning means two recorded authorizations or an open obligation at time t. Never "would have prevented LaGuardia".
  - Say "frequency", not "channel", for radio.
  - Re-voice audio; never redistribute VASAviation audio.
  - "Prediction unavailable" is not "no conflict".
- **LLM (decided by Franco, Oct 3):** `nvidia/Qwen3.6-35B-A3B-NVFP4`, served by the `nemoclaw-vllm` container (NemoClaw provider `vllm-local`, reached from the sandbox as `inference.local`). Nemotron is not used; older docs that say Nemotron are out of date.
- **Speech models:** Whisper large-v3-turbo is the primary ASR. Do not use the jacktol ATC Whisper (deprecated, and trained partly on the ATCO2 test set).

## Commands
- `python3 tests/run_all.py` must stay at 53/53 before every demo change.
- `python3 eval/run_eval.py` scores route_only, motion_only and combined on the six fictional episodes.
- `python3 tools/make_episodes.py --hidden 6 --seed <pick at venue>`, then `python3 eval/run_eval.py SIM_H<seed>_0 ...`, gives the blind test.
- `python3 tools/run_sim_episode.py SIM_E1_CROSS_DURING_ROLLOUT --out ui_scaffold/samples/live.json` builds a display timeline.
- `python3 tools/replay_fixture.py LGA_2026-03-22 --no-speaker-hints` replays the ledger on a historical fixture.

## Where things are
- `docs/RUNBOOK_GB10.md`: vLLM, Whisper and the smoke tests (its Nemotron serving steps are superseded; the model is Qwen3.6 via NemoClaw onboarding).
- `STATUS.md`: venue status log.
- `docs/AGENT_ASSEMBLY_PLAN.md`: what to wire, in what order.
- `lib/gmaps_core/adapters.py`: `transcribe()`, `LocalLLM.parse_residue()`, `TOOL_SCHEMAS`.
- `data/airports/KLGA_CHANGES_draft2.md` and `KBOS_CHANGES_draft2.md`: open questions for a qualified reviewer.

## Team
Franco handles build, runtime, UI and outreach. Rachel is not technical: she handles re-voicing, the video, the pitch and milestone tracking (see `docs/RACHEL_CARD.md`). Ask Franco before re-scoping anything.
