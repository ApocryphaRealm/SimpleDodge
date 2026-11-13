# Simple Dodge 1.2.0 (round 4) - in-game test steps

Package: `D:\Claude output\7. current test builds\Skyrim - Simple Dodge\Simple Dodge 1.2.0` (repo 27c7522 or later).
Round 3 (the owner, by hand, 2026-11-13): first-person dodges work; under True Directional Movement's target lock every
roll went toward the target; the chain should be step, short roll, long roll; Shorter was not seen (it is an installer
choice: step distance "Shorter").

## Setup
1. Njordlinger, profile **Njordlinger Test**. Install **test Simple Dodge 1.2.0** from this package (FOMOD:
   Line-SE-AE16, step distance **Normal**; reinstall with **Shorter** for P2). True Directional Movement enabled.
2. pandora-run (the behaviour did not change since round 3, but run it after any reinstall). `uLogLevel = 1`.
   Expect the log line "True Directional Movement API: found - rolls take its yaw control while they play".

## Checks (game state -> action -> EXPECTED)

### L1 - rolls under a target lock
- `bStepDodge = false`, `bLongRoll = true`, sword drawn, third person, an enemy (or a summoned / placed NPC) TARGET
  LOCKED with TDM. Roll in all 8 stick directions.
  EXPECTED: each roll goes the way the stick points relative to the camera (left = to the left of the target, back = away
  from it), not toward the target. Log per roll: "Roll: turned from A to B", then "Roll: yaw control given back to True
  Directional Movement" about 1 s later; afterwards TDM faces the target again. No "kept its yaw control" line.
- The same with TDM's target lock off (free movement): rolls go the stick's way, as round 3.

### CH - the chain in three stages (`bChainStepToRoll = true`, `fChainWindowStart = 0.40`, `bStepDodge = true`)
- **CH1** Step left; at about 60% of the step press dodge with forward held; at about 60% of that roll press dodge with
  right held. EXPECTED: step, then a short roll forward, then a long roll to the right. Log "Chain: step -> roll (iStep 0)",
  then "Chain: roll -> long roll (iStep 4)". Three "Dodge cost N applied" lines (stamina 100 -> 85 -> 70 -> 55 at 15).
- **CH2** A fourth press during the long roll. EXPECTED: "Chain: refused - the long roll ends the chain", no charge.
- **CH3** A press before 40% of the short roll. EXPECTED: "before the window - ignored"; the roll is not cut.
- **CH4** Under a target lock (L1's setup): CH1 again. EXPECTED: each roll in its pressed direction.
- **CH5** First person: CH1. EXPECTED: step then short roll; the third press is refused ("this behaviour has no long
  roll").

### S1 - dodge while sprinting (default on): as round 3's S1.

### P2 - Shorter (installer option): reinstall with step distance **Shorter**, pandora-run, relaunch; step F / B / L / R.
  EXPECTED about 287 / 180 / 201 / 201 (+ the walk), first and third person, and the four first-person diagonals shorter.
