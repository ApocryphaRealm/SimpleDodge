# Simple Dodge 1.2.0 (round 5) - in-game test steps

Package: `D:\Claude output\7. current test builds\Skyrim - Simple Dodge\Simple Dodge 1.2.0` (repo b5586dd or later).
Owner's round-4 results (2026-11-13, by hand): dodge while sprinting PASS; first-person dodges work; Shorter is to be the
recommended step distance; rolls to become eight directional rolls, each the forward roll turned.

## Setup
1. Njordlinger, profile **Njordlinger Test**. Install **test Simple Dodge 1.2.0** from this package. FOMOD: Line-SE-AE16,
   step distance **Shorter (recommended)** - now the pre-selected choice - and Normal only for R3.
2. pandora-run (the behaviour patch changed: eight roll clips, chain events). Check Engine.log has no node-drop line, and
   1hm_behavior / mt_behavior / magicbehavior .hkx hold "TKDodgeRollLeft", "TKDodgeRollBackRight", "SDGChainRollLeft".
3. `uLogLevel = 1`. True Directional Movement enabled.

## Checks (game state -> action -> EXPECTED)
- **R1** `bStepDodge = false`, `bLongRoll = false`, sword drawn, third person, TDM target lock on an NPC: roll in all 8
  directions. EXPECTED: each roll goes in the pressed direction relative to the character (left = left of the target, back
  = away), the body turns into the roll and ends facing the target again. Log "Dodge: roll (iStep 0) TKDodge<Dir>"; no
  "Roll: turned" line. Distance about 287 under Shorter (0.7 x 409), the same in every direction (+ walk).
- **R2** `bLongRoll = true`: the same 8. EXPECTED about 614 in every direction (long rolls keep their length under Shorter).
- **R3** Reinstall with Normal (Pandora again): standard roll about 409 in every direction.
- **R4** Without the target lock, and sheathed (`bDodgeWhenSheathed = true`, the Unarmed set): rolls in 4 directions,
  each the forward roll turned; open hands when sheathed.
- **CH** `bChainStepToRoll = true`, `bStepDodge = true`: step left; at about 60% press with back held; at about 60% of that
  roll press with right held. EXPECTED: step, short roll BACK, long roll RIGHT. Log "Chain: step -> roll (iStep 0)
  SDGChainRollBack", then "Chain: roll -> long roll (iStep 4) SDGChainRollRight"; three charges; a fourth press refused
  ("the long roll ends the chain"). First person: step, short roll, third press refused.
- **P** Shorter steps (default now): F / B / L / R about 287 / 180 / 201 / 201 (+ walk), third and first person.
- **S1** Dodge while sprinting: PASS in round 4 (the owner) - a quick confirmation only.
