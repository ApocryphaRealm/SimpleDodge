# Simple Dodge 1.2.0 - in-game steps for items 8 (step-to-roll chain) and 9 (forward-roll turn)

These items were built after request 20261112-181850-simple-dodge-1-2-0-sheathed-dodg-5b6d. They need a repackage
(package-mod.ps1 -Mod SimpleDodge -Force, same 1.2.0) and a Pandora run: the patch gained the event SDGChainRoll in
1hm, magic, mt (sheathed) and the three first-person graphs. Same setup as TEST-STEPS-1.2.0.md (Njordlinger Test,
TK Dodge AIO folders disabled, pandora-active-patches-gate --fix, then Pandora through MO2, output mod "Pandora Output").

## Item 9 - every roll is the forward roll, turned to the stick
Setup: `bStepDodge = false` (rolls), `bLongRoll = true`, eight-way on, weapon drawn, third person.
- **F1** Camera behind the player. Roll in all 8 directions (stick or WASD + dodge).
  EXPECTED: for each, the body snaps at once to face the pushed direction and plays the FORWARD roll that way; the log
  says "Roll: turned from A to B" and "Dodge: long roll (iStep 4) TKDodgeForward". No back/side roll clip plays.
- **F2** Turn the camera 90 degrees to the right of the character (weapon sheathed so the camera orbits, `bDodgeWhenSheathed = true`),
  push forward on the stick and roll. EXPECTED: the body faces the CAMERA's forward and rolls that way.
  Repeat with the camera at about 180 and 45 degrees.
- **F3** No direction held (`bEnableDodgeInPlace = true`). EXPECTED: forward roll straight ahead, no turn.
- **F4** First person, drawn, rolls in 4 directions. EXPECTED: the view turns to the pushed direction and the forward
  roll plays (first person rolls the same).
- **F5** Distance: long roll forward about 614 units (both installer choices). With `bLongRoll = false`: about 409 units
  with step distance Normal, about 287 with Shorter - now in every direction, since all rolls use the forward roll.

## Item 8 - chain a step into a roll
Setup: `bStepDodge = true`, `bChainStepToRoll = true`, `fChainWindowStart = 0.40`, weapon drawn, third person.
- **C1** Step dodge left, then press dodge with the stick held forward at about 60% of the step (after the lead foot
  lands). EXPECTED: the step ends in a turn and a forward roll toward the new direction; the log says
  "Chain: step -> long roll (iStep 4)".
- **C2** Press the second dodge at the very start of the step (before 40%). EXPECTED: nothing; the log says
  "Chain: press at ..., before the window ... - ignored"; the step finishes normally.
- **C3** During the chained roll press dodge again. EXPECTED: no third dodge ("Chain: refused - already chained once").
- **C4** `bChainStepToRoll = false`: step, then press in the window. EXPECTED: no roll (the press is refused as
  "Already dodging").
- **C5** Stamina (TestBench): read stamina, step, chain. EXPECTED: two charges, one for the step and one for the roll
  (log: two "Dodge cost N applied" lines), not three. With too little stamina for the roll: no chain, the meter flashes.
- **C6** Sheathed (`bDodgeWhenSheathed = true`), magic drawn, and first person: C1 once each. EXPECTED: the chain works
  in each (sheathed and magic graphs carry SDGChainRoll; first person rolls forward after the turn).
