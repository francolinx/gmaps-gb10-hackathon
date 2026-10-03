# Judge Q&A: short, honest answers

**What is it?**
A controller-side awareness and look-ahead tool. It turns radio speech into typed instructions and keeps what was authorized, read back, reported and observed separate. It treats each runway as a reserved resource, and it projects whether two movers' occupancy windows overlap at a shared zone. Every warning says which two authorizations conflict and what would clear it.

**Isn't this what ASDE-X / surface surveillance already does?**
Surveillance alerts on motion. GMAPS adds the instruction layer: who was told what, whether it was read back, whether a stop was acknowledged, and whether observed motion matches the instruction. Prediction itself isn't new. Our hypothesis is that adding source-linked speech intent to an explicit look-ahead is useful. We haven't measured operational benefit.

**Would it have prevented LaGuardia?**
We don't claim that. What we can show is narrower: with the re-voiced transcript, our ledger held a landing authorization and a crossing authorization on runway 4 at t=+40 s. It also kept the truck's crossing reserved, because the stop calls were never acknowledged. What humans could have done with that is a question for qualified people.

**Is the prediction real or an animation?**
It's real. It runs only on simulated observation packets received up to "now", plus the recorded intent. Truth and expected answers live in a separate folder that only the scoring script reads. A test proves that future packets can't change an earlier prediction. *(Say this only once STATUS.md records it:)* Today we generated unseen episodes with a seed picked on site and scored them blind.

**Why a fictional map?**
The FAA airport diagrams are not survey geometry, and our LaGuardia and Logan graphs are draft topology still pending expert review. We refuse to measure PDF pixels as positions. The look-ahead runs on a declared fictional map until reviewed geometry exists.

**How did you test it?**
- Fifty-three automated checks cover the parser, the ledger on both historical scenarios (with and without speaker labels, on clean and on caption-style text), the variants, separation, no-future-leak, and episode regressions.
- We compared three methods on the same inputs:
  - **authorization-only rules:** missed the hold-short case and alarmed on a safe late crossing.
  - **motion-only:** alarmed on a vehicle that was correctly stopping.
  - **combined:** no misses or false alarms on the six designed episodes. On 12 unseen random episodes before the event (a developer check): 3 hits, 8 correct silences, 1 false alarm.
- These are fictional episodes with a declared model, not operational performance.

**Local? Which models?**
Inference runs on the GB10. The LLM is Qwen3.6-35B-A3B NVFP4 (`nvidia/Qwen3.6-35B-A3B-NVFP4`), served by local vLLM and reached from the NemoClaw/OpenShell sandbox as `inference.local`, with thinking off. It chooses tool calls; it never computes trajectories. The grammar parser handles the safety-critical fields without a model, and the model client refuses non-local endpoints. Whisper large-v3-turbo is the planned ASR. *(As of 13:47 CDT no owned clip had been transcribed on the GB10, so the E1 full-stack run used transcript text.)*

**How does the agent reach the GMAPS tools?**
Unmanaged MCP route over the existing local-inference egress rule. OpenShell 0.0.116 can't pin host.openshell.internal for managed MCP; tool bounds and token enforced server-side; all traffic stays on-box except the Telegram alert from the host.
- The OpenClaw agent `gmaps` is allowed only the five `gmaps__*` tools. Runtime/shell, filesystem, web, UI, automation, sessions, memory, messaging and nodes are denied.
- The tool server runs from an allow-listed runtime folder with no labels, truth or future observation files. A replay process hands it only the packets received up to "now".
- The alert goes out once per open warning, labelled fictional, with rule, actors, look-ahead window and run ID.

**What did you build today vs before?**
Before the event (allowed preparation): the libraries, the fictional fixtures, the display scaffold and the docs. Today: the agent (Qwen3.6 tool calls through NemoClaw/OpenClaw/OpenShell into an MCP tool server wrapping the ledger and look-ahead, plus the Telegram alert), and, if completed, ASR on owned clips, the blind test and the latency measurements. Say only what has a run ID in STATUS.md. The git history shows it.

**What's next?**
A qualified controller reviews the scenarios and the open graph questions. Then reviewed geometry, real timestamped surveillance feeds, and a human-in-the-loop comparison of checking effort and correct conclusions.

**Biggest limitation?**
- Voice alone can't give position.
- Our airport topology is draft.
- Our predictor parameters are engineering choices, not aviation standards.
- We haven't measured benefit to controllers.
