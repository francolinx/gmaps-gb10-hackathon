# Re-voice script

Record each line as its own clip: WAV, mono, 16 kHz or higher, under 10 s. Name it exactly as listed and save it in `~/gmaps/audio/`.

**Two voices:**
- Voice A is the controller.
- Voice B is the pilot or the vehicle driver.

Read it the way it's written, at radio pace. Don't act; a flat, quick delivery is more realistic.

**Why we re-voice:** our own recordings are clean to use and to share. We never use or redistribute VASAviation audio.

**Kokoro alternative:** if there's no time to record, generate clips with Kokoro-82M, which is on the SSD under `models/speech/kokoro-82m`. If you do, label the demo audio as synthetic.

## Part 1: fictional SIM-1 episodes (record these first; they drive the live demo)

Several episodes reuse the same lines. Each line below needs to be recorded only once; the table says which episodes use it.

| # | File | Voice | Line | Used in |
|---|---|---|---|---|
| 1 | `SIM_E1_CROSS_DURING_ROLLOUT_0.wav` | A (ATC) | SimAir two one two, runway three six, cleared to land. | E1, E2, E3, E4, E5, E6 |
| 2 | `SIM_E1_CROSS_DURING_ROLLOUT_3.wav` | B | Cleared to land runway three six, SimAir two one two. | E1, E2, E3, E4, E5, E6 |
| 3 | `SIM_E1_CROSS_DURING_ROLLOUT_24.wav` | B | Tower, Rescue seven, request to cross runway three six at Kilo. | E1, E2, E3, E4 |
| 4 | `SIM_E1_CROSS_DURING_ROLLOUT_28.wav` | A (ATC) | Rescue seven, cross runway three six at Kilo. | E1, E2, E3, E4 |
| 5 | `SIM_E1_CROSS_DURING_ROLLOUT_31.wav` | B | Crossing runway three six at Kilo, Rescue seven. | E1, E2, E3, E4 |
| 6 | `SIM_E3_STOP_NOT_OBSERVED_38.wav` | A (ATC) | Rescue seven, stop, stop, stop. | E3 |
| 7 | `SIM_E5_HOLD_NOT_SLOWING_18.wav` | A (ATC) | Rescue seven, hold short runway three six at Kilo, traffic landing. | E5, E6 |
| 8 | `SIM_E5_HOLD_NOT_SLOWING_21.wav` | B | Hold short runway three six at Kilo, Rescue seven. | E5, E6 |

The agent replays a recorded line at the time T given in each episode's transcript file. The same clip can be reused in every episode that lists it.

## Part 2: LaGuardia, Mar 22 2026 (historical replay, re-voiced)

These lines are re-voiced from public secondary sources (auto-captions of a public reconstruction). Label them on screen as **historical replay · re-voiced · secondary source**.

The scope of the claim is narrow. GMAPS shows that its ledger held two authorizations on runway 4 at t=+40. It does not claim anything would have been prevented.

| File | Voice | Line |
|---|---|---|
| `LGA_-32.wav` | B | Jazz 646 (check-in on tower). |
| `LGA_-30.wav` | A | Delta 520, going to lane 8, just hold short of Lima on runway 13 and verify with the ramp that you'll be able to get in. |
| `LGA_-21.wav` | B | Hold short of Lima on runway 13, we'll talk to ramp and get back to you, Delta 520. |
| `LGA_-15.wav` | A | Just verifying, there's some shuffling of gates going on due to an inbound that had an issue. |
| `LGA_-9.wav` | A | Jazz 646, runway 4, number two. |
| `LGA_+0.wav` | A | Runway 4, cleared to land, number two, Jazz 646. |
| `LGA_+0.wav` | B | 2384, do you have a gate available at this time? Otherwise we will probably be requesting stairs. |
| `LGA_+9.wav` | A | Give me one second, 2384. |
| `LGA_+18.wav` | A | Stand by, United. |
| `LGA_+21.wav` | A | Who's the vehicle needing to cross the runway? |
| `LGA_+25.wav` | A | Emergency vehicles, are you calling on ground or are you calling on tower? |
| `LGA_+25.wav` | B | Truck 1 and company, LaGuardia Tower. |
| `LGA_+34.wav` | B | Truck 1 and company, LaGuardia Tower, requesting to cross 4 at Delta. |
| `LGA_+40.wav` | A | Truck 1 and company, cross 4 at Delta. |
| `LGA_+42.wav` | B | Truck 1 and company, crossing 4 at Delta. |
| `LGA_+48.wav` | A | Frontier 4195, just stop there please. Stop, stop, stop. Truck 1, stop, stop, stop. |
| `LGA_+55.wav` | A | 2384, you're cleared in lane 8 for gate 41. 2384, proceed to the ramp. |
| `LGA_+65.wav` | A | Sorry. Truck 1, stop. Truck 1, stop, stop. Truck 1, stop. |
| `LGA_+72.wav` | B | 4195, we're staying here. |
| `LGA_+76.wav` | A | Delta 263, go around, runway heading, 2000. |
| `LGA_+76.wav` | A | 646, I see you collided with a vehicle. |
| `LGA_+83.wav` | A | Just hold position, I know you can't move. The vehicles are responding to you now. |
| `LGA_+92.wav` | A | 263, go around, runway heading, 2000. |
| `LGA_+92.wav` | B | Right, 2000, go around, 263. |

## Part 3: Logan, June 20 2026 (NTSB preliminary DCA26LA242, Table 1; historical, re-voiced)

| File | Voice | Line |
|---|---|---|
| `BOS_+0.wav` | A | American 3161, runway 27, line up and wait. Traffic landing runway 33L. |
| `BOS_+0.wav` | B | Line up and wait runway 27, American 3161. |
| `BOS_+14.wav` | A | Delta 2351, runway 33L, cleared to land. Traffic holding on runway 27. |
| `BOS_+14.wav` | B | Cleared to land 33L, Delta 2351. |
| `BOS_+82.wav` | A | American 3161, runway 27, cleared for takeoff. |
| `BOS_+85.wav` | B | Cleared for takeoff 27, American 3161. |
| `BOS_+101.wav` | A | Tradewind 82, turn left on taxiway Tango, expedite, traffic on a one-and-a-quarter-mile final. |
| `BOS_+119.wav` | A | Tradewind 82, continue on runway 27, turn left on taxiway Tango. |
| `BOS_+130.wav` | A | Tradewind 82, additional taxi instructions. |
| `BOS_+144.wav` | B | Delta 2351 is going around, due to the American. |
| `BOS_+149.wav` | A | American 3161, where are you going? |
| `BOS_+164.wav` | A | Delta 2351, go-around instructions. |

## Part 4: the clipped-readback case (fictional; good for showing ASR uncertainty)

| File | Voice | Line |
|---|---|---|
| `CLIP_+0.wav` | A | Cobalt 41, runway 13, taxi via Alpha, Delta, hold short runway 4. |
| `CLIP_+6.wav` | B | Runway 13, Alpha, Delta, ho— (stop talking mid-word) |
| `CLIP_+9.wav` | A | Cobalt 41, you were clipped, say again, and read back hold short runway 4. |
| `CLIP_+13.wav` | B | Alpha, Delta, hold short runway 4, Cobalt 41. |
