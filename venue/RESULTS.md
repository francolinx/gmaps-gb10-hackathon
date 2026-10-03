# GMAPS results (measured at the venue, Oct 3 2026, Dell GB10)

Everything below was observed on the GB10 today. Each line names its run ID; traces are in `venue_traces/` and the full log is in `STATUS.md`. **All traffic is fictional:** map SIM-1, airport XSIM, simulated observations, re-voiced fictional radio lines. Nothing here is a real airport or real traffic, and nothing here claims operational benefit or accident prevention.

## Stack actually used
- Speech: **Whisper large-v3-turbo**, local weights, fp16 on the GB10 GPU, run in an offline (`--network none`) throwaway container from the existing vLLM image.
- LLM: **`nvidia/Qwen3.6-35B-A3B-NVFP4`** on local vLLM, reached from the NemoClaw/OpenShell sandbox as `inference.local`. In every agent turn the executionTrace reported `winnerProvider=inference`, `fallbackUsed=false`.
- Agent: OpenClaw agent `gmaps` (OpenClaw 2026.7.1, NemoClaw 0.0.124, OpenShell 0.0.116) with **only five tools**: `gmaps__parse_transmission`, `ledger_ingest`, `lookahead`, `open_warnings`, `post_alert`. Shell, filesystem, web, UI, automation, sessions, memory and messaging tools are denied.
- Tools: a deterministic GMAPS tool server on the host, running from an allow-listed runtime folder that contains no evaluation labels, no truth files and no future observations. A separate replay process hands it only the packets received up to "now".
- Alerts: Telegram, sent from the host by a **deterministic template built from tool results only**. No model text is ever sent.

**Route note:** the agent reaches the tools over an **unmanaged MCP route over the existing local-inference egress rule**. OpenShell 0.0.116 can't pin host.openshell.internal for managed MCP, so tool bounds and the token are enforced server-side. All traffic stays on-box except the Telegram alert from the host.

**Cloud egress removed:** the `nvidia` (integrate.api.nvidia.com) and `huggingface` (incl. router.huggingface.co) entries were removed from the sandbox policy. Afterwards `inference.local` still answered and python3 → HF router returned 403.

## Measured results
| What | Result | n | Run IDs |
|---|---|---|---|
| E1 crossing during rollout, full stack, Whisper input, back to back | **3/3 pass** (R1 at t=28; one POSSIBLE CONFLICT alert; look-ahead raised overlap at Z1, 47.3–72.8 s, lead 19.3 s) | 3 | e1demo-20261003-143811-030f, -143959-5d15, -144142-a52a |
| Clip-to-alert (Whisper on the t=28 clip + agent turn until Telegram accepted the alert) | **12.83 s, 13.96 s, 16.0 s** (median 13.96 s) | 3 | same |
| Whisper per clip, warm, GPU (decode excluded) | median **0.21 s** (0.181–0.229 s); cold load + first clip 12.1 s | 8 clips | asr_140059 |
| Agent turn wall time (one transmission → reply) | 11.8–34.2 s across runs; E1 video run median 19.4 s | 5 per run | e1demo-20261003-141347 |
| E2 same paths, later crossing | Look-ahead **never raised** an overlap; the ledger R1 still fired → alert tiered **"AUTHORIZATION CHECK, no predicted overlap from this check"** | 1 | e2demo-20261003-142714 |
| E3 stop not observed (stop call via Whisper) | Stop ingested as CANCEL; the look-ahead **kept the overlap raised** at 38/42/48 s while motion continued | 1 | e3demo-20261003-142924 |
| E4 feed loss (clock ticks 38, 44) | At t=44: "last observation 9.0 s old (> 6.0 s): timed prediction withdrawn" → **UNAVAILABLE**, not "no conflict" | 1 | e4demo-20261003-142003 |
| E5 hold read back, not slowing (clips via Whisper; ticks 30, 40) | At t=40: **hold_exceedance raised** + overlap raised. No ledger rule fired, so no phone alert (UI only) | 1 | e5demo-20261003-143228 |
| E6 hold honoured (text; same ticks as E5) | Overlap **conditional only** at 21/30/40, never raised; no alert | 1 | e6demo-20261003-143449 |
| Can OpenClaw tool search reach non-GMAPS tools? | **No.** The full catalog lists only the 5 gmaps tools; `tool_call` exec/read/web_fetch → "Unknown tool id" | 2 probes | toolsearch-probe, -probe2 |
| Prepared library checks | 53/53 | 53 | `tests/run_all.py` |

## Known limits (observed today)
- **ASR errors are kept as heard:** "367R212", "Resco 7", "RISCO 7", "Tour". A misheard callsign leaves the parse with **no actor** (E1 readbacks and request; E5 readback). No repair rules were tuned to these clips.
- **Input modes differ by episode:** E1 used Whisper on all lines; E3/E5 mixed Whisper (the clipped lines) with transcript text (the rest); E2, E4 and E6 used transcript text only. Each run's mode is shown on screen and stated in the alert.
- **Clip-to-alert excludes** Whisper's cold start (~12 s, once per run) and audio decoding, because ASR runs as a batch before the agent turns. No display-latency figure was measured.
- **The model is not perfectly reliable:**
  - It once alerted before running the look-ahead. One phone message carried a stale look-ahead line; the server now forces a fresh look-ahead before any alert.
  - It sometimes parses a line twice, and once sent 5 empty-argument calls (all rejected by the server, then it recovered).
  - Its prose has paraphrased loosely ("on final" during rollout, an invented search result). Prose appears in the UI only, labelled "agent summary (unverified)".
- **Alerts are tied to ledger warnings.** A look-ahead-only cue (E5) shows in the UI but is not sent to the phone.
- The predictor parameters are declared engineering choices, not aviation standards. The LGA/BOS graphs are draft topology for identifier lookup only (no geometry, no routing).
- E1–E6 were designed before the event; they are **regression cases, not a blind test**.
- The blind test scored the **library pipeline, not the agent** (see below).

## Blind test (fresh seed, picked live)
- Seed **56774**, picked 14:46:14 CDT. 6 hidden episodes (`tools/make_episodes.py --hidden 6 --seed 56774`). Label sha256s were recorded and **committed before scoring** (commit 3cf603b; `venue_traces/blind_label_hashes.txt`).
- **System scored: the prepared GMAPS library pipeline** (parse → ledger → look-ahead, per-second frames) through `eval/run_eval.py`, **not the OpenClaw agent**. The agent requests a look-ahead only per transmission or tick, and the scorer needs per-second frames; adapting it was not possible before the freeze. The agent's tools call this same deterministic code.
- Result (n=6, only **1** positive episode, so a small sample):

| method | TP | TN | FP | FN |
|---|---|---|---|---|
| route_only (authorization rules only) | 1 | 4 | 1 | 0 |
| motion_only (observations, no intent) | 1 | 1 | 4 | 0 |
| **combined (GMAPS)** | **1** | **5** | **0** | **0** |

- In the positive episode, combined raised at t=33 with a 30.0 s lead before the reference time (62.965 s). Fictional episodes, declared model; not operational performance.
