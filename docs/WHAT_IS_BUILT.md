# What is built vs not (as of Sat Oct 3, ~03:45 ET, before the event)

## Built and tested (prepared libraries, fixtures, scaffold)

| Piece | Evidence |
|---|---|
| Grammar-first parser | The fixtures label 32 transmissions as safety-critical (clearances, crossings, holds, LUAW, stops, go-arounds, taxi). The parser types 31 of them correctly, both with and without speaker labels. The one miss is the placeholder line "additional taxi instructions", which has no content to parse. Conversational lines ("we had an anti-ice light") go to the residue path for the local language model. Use `tests/parse_scan.py` to see every line. |
| Ledger + rules R1–R13 | LGA: R1 CONFLICT at t=+40. No flag on the t=−577 negative case. R13 for the unacknowledged stop to TRUCK1. |
| | BOS: R4 CONFLICT at t=+82, cleared at the go-around at t=+144. |
| | Clipped readback: R7 CAUTION, cleared by the full readback. |
| | Taxi exercise: no warnings. N/A/E coverage is reported as unresolved, not as clear. |
| | All of the above hold in four input modes: speaker hints on or off, clean or caption-style text. |
| Variants A/B/C | R6 possible crossing at D (draft graph), R7 discrepant readback, R8 crossing not closed. |
| Same physical runway | 04 and 22 count as the same runway (R3 test). |
| Look-ahead predictor (fictional SIM-1) | Departure hypothesis after a crossing clearance, hold-short consistency check, stale-data withdrawal. Prediction keeps the moving hypothesis when a stop is unacknowledged. |
| Separation / no-future-leak | Tested. The predictor never reads truth or labels. |
| Graphs | `validate.py --self-test`: both airports, 0 errors, 32/32. Extra BOS checks: 15/15. |
| Display scaffold | Offline single-file page. Renders SIM episodes (map, occupancy bars, look-ahead cards) and historical replays (runway reservation bars). Screenshots checked, no console errors. |

**Total:** `tests/run_all.py` passes 53/53.

## Three-method comparison on the same inputs (fictional, declared model)

Six designed episodes:

| | route_only (rules) | motion_only | combined (GMAPS) |
|---|---|---|---|
| E1 cross during rollout | TP, 24 s lead | TP, 18 s | TP, 24 s |
| E2 same paths, later | **FP** | TN | TN |
| E3 stop not observed | TP | TP | TP (persists after stop) |
| E4 feed loss | TP | TP | TP, then withdrawn |
| E5 hold read back, not slowing | **MISS** | TP, 25 s | TP, 9 s |
| E6 hold read back, slows | TN | **FP** | TN |

Developer check on 12 unseen random episodes (seed 9090, generated after tuning):

| Method | TP | TN | FP | MISS |
|---|---|---|---|---|
| combined | 3 | 8 | 1 | 0 |
| motion_only | 3 | 5 | 4 | 0 |
| route_only | 2 | 3 | 6 | 1 |

**Caveats:**
- I tuned the model while looking at E1–E6, so those six are not a blind result.
- The 12-episode check used a fresh seed but the same generator.
- **Run a new blind test at the venue with a seed you pick there.**
- Lead times are seconds on a fictional timeline, not a measured warning advantage.

## Not built (venue work or later)

- **The agent:** ASR → Nemotron tool calls via NemoClaw/OpenClaw/OpenShell → libraries → display → channel. Organizer rule: built today.
- **Live ASR:** `adapters.transcribe()` exists but is untested on the GB10.
- **Local LLM:** `adapters.LocalLLM` exists but is untested.
- **vLLM container:** not pulled yet.
- **Audio-level clip detection:** the parser only sees text.
- **Real airport geometry and real surveillance feeds:** none exist, by design.
- **Human-factors evaluation:** not done.
- **Qualified controller review:** of the scenarios, the rules, and the graph questions.
