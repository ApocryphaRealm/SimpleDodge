# Simple Dodge 1.2.0 (round 2) - in-game test steps

Package: `D:\Claude output\7. current test builds\Skyrim - Simple Dodge\Simple Dodge 1.2.0` (repackaged; includes the
step-to-roll chain, rolls turned to the stick, the input-buffer fix and the bow note). Round 1 result: batch
B-20261112-181917-d389.

## Setup
1. Njordlinger, profile **Njordlinger Test**. Reinstall **test Simple Dodge 1.2.0** from this package
   (install-test-build.py). FOMOD: Line-SE-AE16, step distance **Normal**. Keep **test Simple Dodge 1.1.0**,
   **test TK Dodge AIO 1.1.0** and **unpublished TK Dodge AIO** disabled.
2. **Bow Rapid Combo V3 (installer page "Compatibility"):** for B1 install with **Use Simple Dodge's bow steps over Bow Rapid Combo V3**. It puts an OAR user.json beside Simple Dodge's Bow config.json, raising it to priority 9901700. For B2 reinstall with the default **Bow Rapid Combo V3 keeps its bow dodges**, which installs nothing. Bow Rapid Combo V3 itself stays enabled for both. No separate override mod is needed.
3. **Behaviour regeneration (required, the patch changed):**
   - `py -3 "D:\Claude output\.MD\scripts\gates\pandora-active-patches-gate.py" --fix`
   - Run `D:\Modlists\Njordlinger\mods\Pandora Behaviour Engine Plus\Pandora Behaviour Engine+.exe` through MO2
     (`--auto_run --auto_close`). The output mod is **Pandora Output**.
   - Check: the Pandora log lists "Simple Dodge", and `Pandora Output\meshes\actors\character\behaviors\1hm_behavior.hkx`
     contains "SDGChainRoll" (the new event).
4. `uLogLevel = 1`. Watch `Simple Dodge.log` live.
5. **Notes for whoever runs it:**
   - Raise CarryWeight (`player.modav carryweight 1000`) BEFORE adding test weapons, or every press is refused as
     overencumbered.
   - Set the time to noon (`set gamehour to 12`) for readable frames.
   - True Directional Movement makes SHEATHED dodges (and sometimes drawn ones) face the pressed direction and step
     forward ("TDM Free Movement, Force to Forward Dodge!"). Do the directional checks with the weapon drawn and the log
     showing the 8-way angle, or in first person.

## Checks (game state -> action -> EXPECTED)

### Bow (8 directions)
- **B1** Installer option "Use Simple Dodge's bow steps over Bow Rapid Combo V3". Bow drawn, step dodge on, eight-way on, third person. Dodge in all 8
  directions; save frames.
  EXPECTED: each is a grounded step holding the bow (bow_idledrawn grip), no flips. Back is about 318 units, not 508.
- **B2** Reinstalled with the default "Bow Rapid Combo V3 keeps its bow dodges" (no user.json in the Bow folder), the same 8 dodges.
  EXPECTED: back, left and right play Bow Rapid Combo V3's flips (its "Base 2", priority 9901001); forward and the
  diagonals are ours. This confirms the cause.

### Forward-roll turn (item 9), F1-F5
Setup: `bStepDodge = false`, `bLongRoll = true`, weapon drawn.
- **F1** Camera behind; roll in 8 directions. EXPECTED: the body snaps to the pushed direction and plays the FORWARD roll.
  Log: "Roll: turned from A to B", "Dodge: long roll (iStep 4) TKDodgeForward".
- **F2** Sheathed (`bDodgeWhenSheathed = true`), camera orbited 90, 180 and 45 degrees; push forward and roll.
  EXPECTED: rolls toward the camera's forward each time. (TDM may already turn the body; the result is the same.)
- **F3** No direction held. EXPECTED: forward roll straight ahead, no turn line.
- **F4** First person, drawn, 4 directions. EXPECTED: the view turns to the pushed direction, forward roll.
- **F5** Long roll forward about 614 units; with `bLongRoll = false` about 409 (Normal) in every direction.

### Chain (item 8), C1-C6
Setup: `bStepDodge = true`, `bChainStepToRoll = true`, `fChainWindowStart = 0.40`, weapon drawn.
- **C1** Step left, then at about 60% of the step press dodge with forward held. EXPECTED: turn + forward roll;
  log "Chain: step -> long roll (iStep 4)".
- **C2** Second press at the very start of the step. EXPECTED: nothing; log "Chain: press at ..., before the window ... -
  ignored".
- **C3** Press again during the chained roll. EXPECTED: no third dodge; log "Chain: refused - already chained once".
- **C4** `bChainStepToRoll = false`: step, press in the window. EXPECTED: no roll.
- **C5** TestBench stamina before, after the step, after the chain. EXPECTED: exactly two charges (two "Dodge cost N
  applied" lines). With too little stamina for the roll: no chain, one refusal line.
- **C6** Once each: sheathed (`bDodgeWhenSheathed = true`), a spell drawn, first person. EXPECTED: the chain works in each.

### Shorter option (its own Pandora run)
- **P1** (Normal, after setup) forward/back/left step on flat ground. EXPECTED about 409 / 300 / 251 units.
- **P2** Reinstall choosing **Shorter**, run Pandora again (setup step 3), relaunch, repeat. EXPECTED about 287 / 180 /
  201. The long roll is unchanged (about 614). With `bLongRoll = false` the forward roll is about 287. Report any foot
  sliding.

### Overencumbered: one log line per press
- **O1** Player over carry weight (`player.modav carryweight -1000`), press dodge 5 times.
  EXPECTED: per press, one "Dodge failed because of: Actor is overencumbered" (plus at most one "Dodge Cost after" line).
  About 10 lines in all, not hundreds. Restore carry weight afterwards.
- **O2** Stamina at 0 (`player.damageav stamina 1000`), press 5 times. EXPECTED: one "Not enough stamina" line per press
  and one meter flash.

### Weapon-type keyword sets (item 11) and the one-handed thigh check
The profile has **Object Categorization Framework** enabled, and **Animated Armoury** and **Heavy Armory** are NOT
installed. Do not add them to the owner's list.
- **K1** After the game reaches the main menu, read Open Animation Replacer's log
  (`Documents\My Games\Skyrim Special Edition\SKSE\OpenAnimationReplacer.log`; its UI is off, bEnableUI = false).
  EXPECTED: all 25 Simple Dodge submods are listed:
  - Unarmed 100;
  - vanilla types 110-120;
  - the 13 keyword sets 131-154.
  The 9 Animated Armoury and Heavy Armory submods (131-136, 141-143) may be reported with an unresolved or invalid
  keyword form (NewArmoury.esp is not loaded; the Heavy Armory keywords B07776-B07780 in Update.esm's range do not
  exist). The 4 OCF submods (151-154) resolve, since OCF is loaded. No other Simple Dodge submod is reported, and no error
  stops OAR from loading. Copy every line that names Simple Dodge.
- **K2** With those submods present, re-check the vanilla-type sets: sword, greatsword, battleaxe, bow (both installer
  choices as in B1/B2) and a spell, drawn, Left and Back. EXPECTED: each still plays its own weapon set, as in round 1.
- **K3** (only if a weapon carrying an OCF polearm or katana keyword exists in the list - search with houseCARL for
  WEAP records with OCF_WeapTypePole2H_Swing, Pole2H_Thrust, Quarterstaff2H or Katana1H) equip it and dodge in 4
  directions. EXPECTED: the matching new set (halberd, pike, quarterstaff or katana grip) plays, not the vanilla-type
  set. If no such weapon is in the list, say so.
- **T1** Iron sword drawn (left hand empty), step dodge Forward-Right; save the frames around its landing (clip frame 11
  of 22, about 0.35 s after the press). EXPECTED: the blade passes beside the right thigh, not through it. The
  offline check measured 5.1 units between the blade axis and the thigh bone at that frame. If the blade visibly cuts
  into the leg, say so with the frame.

### Sheathe after dodging
- **H1** Raise carry weight. Equip an iron sword and an iron shield through the inventory menu (not EquipItemEx), draw,
  dodge 8 times, then press R. EXPECTED: the weapon sheathes.
- **H2** The same, equipped with `player.equipitem` / EquipItemEx as round 1 did. If it will not sheathe, read
  `bIsDodging` and `iStep` through TestBench and check the log for a dodge still in progress.
  The DLL hooks only SprintHandler and SneakHandler (ProcessButton), plus the player and main update loops. It never
  sets a weapon-drawn state or handles the ready-weapon control. So if H2 fails while H1 passes, report it as an
  equip-path issue.
