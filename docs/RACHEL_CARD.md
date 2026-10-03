# Rachel's card: no coding needed

Franco builds the agent. You own the **voice, the story, the video, the clock and the claims check**. In priority order:

## 1. Record the 8 demo lines (first 30 minutes)
- **What:** the 8 lines in Part 1 of `REVOICE_SCRIPT.md`. You read the controller lines (voice A); Franco or anyone else reads the pilot and truck lines (voice B).
- **How:**
  - Use a phone voice-memo app in a quiet corner.
  - Use one take per line, with half a second of silence before and after.
  - Name each file exactly as in the table and AirDrop or send it to Franco.
- **If time allows:** record Part 3 (Logan, 7 lines) and Part 4 (clipped, 4 lines). For the clipped line, stop talking mid-word on purpose.

## 2. Keep the clock (all day; post times in the team chat)
| Time | Checkpoint | If it's missed |
|---|---|---|
| 10:30 | Models answering on the GB10 (Franco says "Nemotron ready") | Ask Franco if he wants a mentor |
| 12:00 | One clip goes in, a typed event comes out | Tell Franco to fall back to transcript replay and label it |
| 13:30 | E1 shows the conflict and the look-ahead on screen | Cut extras; keep E1, E2 and E5 only |
| 15:30 | **Feature freeze.** No new features after this. | — |
| 16:30 | Start recording the video | — |
| 17:30 | Submit. **Don't wait for 18:00.** | — |

## 3. The ≤3-minute video (storyboard)
1. **(0:00–0:20)** Title card: "GMAPS: understand the instruction, see the evidence, look ahead." Add a "fictional exercise" label.
2. **(0:20–0:55)** Play E1 audio clips live. The screen shows the transcript turning into typed events, then the R1 conflict card with its explanation.
3. **(0:55–1:25)** Look-ahead: the occupancy bars overlap before the vehicle reaches the runway. Open the card's assumptions.
4. **(1:25–1:50)** E2: same paths, later crossing, and no look-ahead overlap. Point out that the authorization rule alone would still alarm.
5. **(1:50–2:10)** E5: "hold short" was read back, but the truck isn't slowing, and GMAPS flags it. Then E4: the feed drops and the prediction is withdrawn, not guessed.
6. **(2:10–2:40)** Real GB10 runtime (terminal plus nvidia-smi), the blind-test result table, and one sentence on next steps (qualified controller review).
7. **(2:40–3:00)** Closing line, plus the team.

Record screen captures with Franco's laptop or OBS. Keep the captions short.

## 4. Claims check (read every slide and caption against this)
| Never say | Say instead |
|---|---|
| "Would have prevented LaGuardia" | "At t=+40 the ledger held two authorizations on runway 4." |
| "Predicts collisions" | "Projects occupancy windows on a fictional map from simulated observations." |
| "Channel 1/2" (for radio) | "Frequency" |
| "AI controller", "replaces controllers" | "The controller stays the decision-maker; GMAPS makes the evidence checkable." |
| Any accuracy % we didn't measure today | Only numbers from today's blind test, with their count |
| "Real LaGuardia map" | "Draft topology pending expert review; the look-ahead uses a fictional map." |

## 5. Judge Q&A
Read `JUDGE_QA.md` once and take the "context" questions so Franco can take the technical ones.

## 6. Submission checklist (17:00)
- [ ] Video at most 3 minutes, uploaded, and the link opens in a private window
- [ ] Repo link, with README first
- [ ] Write-up that says what was prepared before the event versus built today
- [ ] Hardware questions answered (GB10; models used: Nemotron 3 Nano NVFP4, Whisper large-v3-turbo)
- [ ] Measured numbers only
