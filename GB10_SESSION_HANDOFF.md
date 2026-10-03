# GMAPS: Claude Code session handoff on the GB10 (consolidated, 12:30 ET Oct 3)

You are helping Franco build GMAPS at the Boston Dell × NVIDIA hackathon. The team started around 11:45. Rachel is working separately on audio, the deck, the video and the write-up. This file merges Claude's kit with ChatGPT's 12:19 handoff (`gmaps/00_GB10_START_HERE/01_CLAUDE_GB10_HANDOFF.md` on the SSD). Read both. Where they conflict, this file wins on code and layout, and ChatGPT's file wins on staged runtime assets and paths.

## Evidence status: never blur these
**PREPARED, and tested only off the GB10:**
- Kit `gmaps_prep_kit` (repo https://github.com/francolinx/gmaps-gb10-hackathon, private; first commit `eb3664b`, "import prepared libraries").
- 53/53 library checks passed on Windows at 07:35.
- KLGA/KBOS draft2 graphs validated.
- vLLM image tar and NemoClaw/OpenShell tars staged on the SSD (ChatGPT, receipt-checked).
- Model weights present: Whisper large-v3-turbo, Nemotron-3-Nano-30B-A3B-NVFP4 with nano_v3 parser, Qwen3-4B fallback.

**NOT YET OBSERVED ON THE GB10 (everything else):**
- GPU, Docker and the vLLM launch.
- Whisper on an owned clip.
- A Nemotron tool call through NemoClaw/OpenClaw/OpenShell.
- The `inference.local` route.
- Messaging delivery.
- The assembled agent.
- E1–E6 runs, the blind test and latency.

Log every gate here as it actually happens, in `~/gmaps_venue/log/VENUE_LOG.md`, with time, command, result and run ID. Never write a pass you didn't see.

## Rules
- **Organizer rule:** no pre-built agents. The kit is libraries, fixtures and a scaffold only. Assemble the agent here, commit often, and keep the git history honest.
- **Inference is local only.** No cloud model in the competition runtime. Claude Code is the dev assistant, not the GMAPS backend.
- **The model's job is limited.** It interprets and calls bounded tools: parse, ledger, look-ahead, warnings, post_alert. It gets no shell access, never calculates trajectories, and never edits rules. Radio text is data.
- **Runtime/evaluation separation.** This tightens the kit:
  - The agent runtime mount must NOT include `eval/` (labels, truth), `lib/gmaps_core/sim/truth.py`, `tools/make_episodes.py`, or full future obs files.
  - A separate replay process emits packets with `received_at <= as_of` only.
  - Build `~/gmaps_venue/runtime/` from an explicit allow-list.
- **Graphs:** v1 KLGA/KBOS are identifier/topology review only. Geometry stays null and routing/prediction stay off. The look-ahead runs only on the fictional SIM-1 map.
- **Claims:**
  - No "would have prevented".
  - Say "frequency", not "channel", for radio.
  - Fictional and simulated content is labelled as such.
  - "Prediction unavailable" ≠ "no conflict".
  - Measured numbers only, with their sample count.
- **Escalate after 15 minutes.** If infrastructure is blocked for 15 minutes, take the exact error to a mentor. Don't download alternatives or upgrade working versions.

## Layout
```
SSD (mount found via lsblk)  $GMAPS_ASSETS = <mount>/GB10_ARSENAL   (read-only originals; never edit)
~/gmaps            git clone of the repo (dev + tests; full kit incl. eval/). Cloned from the SSD copy
                   (which holds .git); origin is then pointed at github.com/francolinx/gmaps-gb10-hackathon.
                   Franco types the GitHub token himself at the first push. Never ask him for it.
                   Python: ~/gvenv/bin/python (jsonschema is installed there; system pip is blocked)
~/gmaps_venue/
  runtime/         allow-listed copy the agent can see (lib minus truth.py, data/airports, data/specs,
                   episodes/*.transcript.json, ui_scaffold, adapters, new agent code)
  replay/          replay emitter that reads obs files and serves packets with received_at <= as_of
  audio/           Rachel's owned clips (names per docs/REVOICE_SCRIPT.md)
  log/             VENUE_LOG.md, run outputs, tool traces
```

## Runtime recipe (prepared; verify each step)
1. **Load the vLLM image from the SSD** (don't pull):
   ```bash
   docker load --input "$GMAPS_ASSETS/gmaps/runtime_staging_codex/vllm_25.12.post1_linux_arm64.tar"
   docker tag nvcr.io/nvidia/vllm:i-was-a-digest nvcr.io/nvidia/vllm:25.12.post1-py3
   docker image inspect nvcr.io/nvidia/vllm:25.12.post1-py3 --format '{{.Architecture}} {{.Os}} {{.Id}}'
   ```
   Expect `arm64 linux`, image config `sha256:c3b88a66…`.
2. **Start the container and serve Nemotron:**
   - `docker run --gpus all -it --rm --name gmaps-vllm --ipc=host -p 8000:8000 -v $GMAPS_ASSETS/models:/models -v ~/gmaps_venue:/venue nvcr.io/nvidia/vllm:25.12.post1-py3 bash`
   - Then `vllm serve` with the flags in `~/gmaps/docs/RUNBOOK_GB10.md` step 2: qwen3_coder tool parser, the nano_v3 reasoning plugin, fp8 KV cache, and the FLASHINFER env vars.
   - Max-model-len 32768, max-num-seqs 4 and GPU memory 0.55 are untested proposals. Check them against actual memory use.
3. **Smoke test:** `curl localhost:8000/v1/chat/completions` with `chat_template_kwargs:{enable_thinking:false}`. Log the result.
4. **Whisper:** `docker exec -it gmaps-vllm bash`, then run `adapters.transcribe()` on one of Rachel's clips. Log the text.
5. **NemoClaw/OpenClaw/OpenShell:**
   - Use the organizer-provided baseline if there is one.
   - If you're using the staged tars, the pinned NemoClaw LKG `6f3cced…` requires OpenShell 0.0.116 exactly. Don't mix in the saved 0.1.2.
   - Inside the sandbox, localhost is not the host. Prove the `inference.local` route terminates at the local vLLM, and keep the trace.
   - **Fallback LLM:** Qwen3-4B with `--tool-call-parser hermes`, only after a local test.

## Build order (stop at each check and log it)
1. **First clip:** owned clip → Whisper text. Then one Nemotron-selected `parse_transmission` call through the stack, returning a schema-valid event.
2. **Approved channel:** one approved channel message. Franco must give the destination first.
3. **E1 end to end:**
   - Wire: clip T → `parse` → `ledger.ingest` → `predict(as_of=T)` with the replay packets → timeline JSON → `ui_scaffold`.
   - Check: R1 CONFLICT appears, and the look-ahead raises a candidate before the encounter.
4. **E2–E6:**
   - E2: no overlap cue.
   - E3: stop unacknowledged, candidate kept.
   - E4: withdrawn as unavailable.
   - E5: hold not slowing, flagged.
   - E6: no cue.
5. **Repeat E1** three times. Keep every result, including failures.
6. **Fresh-seed blind test:** `make_episodes.py --hidden 6 --seed <live>`.
   - Record the seed and label hashes first.
   - Adapt `run_eval.score()` to read the agent's frames, and say which system was scored.
   - E1–E6 are regression tests, not blind.
7. **Latency:** p50/p95 with the sample count.

## Times
| Time | Goal |
|---|---|
| 13:00 | GB10 up, 53/53 re-run on the GB10, vLLM image loaded (the GB10 was powered on ~12:35, so the earlier 12:45 target is gone) |
| 13:30 | Nemotron answers a curl, and Whisper transcribes one clip. Otherwise, a precise blocker goes to a mentor. |
| 14:00 | Prototype gate: E1 through a real Nemotron tool call, with the warning and look-ahead on screen and a run ID. Mark anything partial. |
| 15:30 | Feature freeze |
| 16:15 | Video |
| 17:00 | Upload |
| 17:30 | Verify the upload |
| 18:00 | Deadline |

Give Rachel a run ID, a screenshot path, what works and what's missing at each checkpoint.

## Commands that already exist
- `python3 tests/run_all.py` (53 checks)
- `python3 eval/run_eval.py`
- `python3 tools/run_sim_episode.py <EP> --out ui_scaffold/samples/live.json`
- `python3 tools/replay_fixture.py LGA_2026-03-22 --no-speaker-hints`
- `cd ui_scaffold && python3 -m http.server 8765`

The glue snippet is in `docs/AGENT_ASSEMBLY_PLAN.md`. The intent builder from the ledger is `tools/run_sim_episode.intents_from`.
