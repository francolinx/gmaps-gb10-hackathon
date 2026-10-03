# Demo arc (live pitch, about 2.5 min)

What to show at each point is mapped to files in the kit. If the live agent isn't ready, show the scaffold with `samples/` and **say it's a replay**.

| Time | Say | Show |
|---|---|---|
| 0:00 | "Controllers have to connect what they told people with what moving aircraft and vehicles might do next. GMAPS makes that connection checkable." The exercise is fictional. | Title, then the display with the FICTIONAL badge |
| 0:20 | "Here's a live radio exchange." Play the E1 clips. | Transcript lane: speech-act chips and typed events from **live ASR** |
| 0:45 | "Two authorizations need the same runway. Here's which ones, and what would clear it." | R1 CONFLICT card |
| 0:55 | "Separately, simulated surveillance drives the look-ahead. The overlap shows up before the truck reaches the runway, and you can open its assumptions." | Map plus occupancy bars, LOOK-AHEAD card |
| 1:25 | "Same paths, different timing: the rule alone would still alarm, but the look-ahead shows no overlap." | E2 |
| 1:40 | "The truck read back 'hold short' but isn't slowing." | E5 hold-short card |
| 1:55 | "We lose the truck's feed, so we withdraw the precise prediction instead of inventing one." | E4 UNAVAILABLE card |
| 2:10 | "All of this runs locally on this GB10. Here's today's blind test on episodes generated on site." | Terminal: `eval/run_eval.py` table, plus nvidia-smi |
| 2:25 | "Understand the instruction. See the evidence. Look ahead." | — |

**If asked about LaGuardia:** open `samples/LGA_2026-03-22.json`. "At t=+40 the ledger held two authorizations on runway 4. The stop calls were never acknowledged, so the crossing stayed reserved." Do not say "prevented".

**Backup if the GB10 fails during judging:** use the laptop with `ui_scaffold` and the samples, and say plainly that it's a recorded replay of today's run.
