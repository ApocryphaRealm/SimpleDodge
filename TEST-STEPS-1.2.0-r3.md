# Simple Dodge 1.2.0 (round 3) - in-game test steps

Package: `D:\Claude output\7. current test builds\Skyrim - Simple Dodge\Simple Dodge 1.2.0` (repo eb07069). Round 2 result:
batch B-20261113-031456-c03f (FAIL on F5, P2, F4 finding, C4 log noise; T1 not judged). Only those steps, plus a quick
regression on B1 / C1 / F1.

## What changed, and the cause it answers
Animation Motion Revolution (AMR, in this profile) moves the character by the motion stored in each clip's own .hkx
("animmotion" annotations) and ignores animationdatasinglefile when a clip has them (AMR's Hooks.cpp). Every Simple
Dodge clip has them. So the long roll, which played the standard roll's file, went as far as the standard roll, and
Shorter, which changed only the motion data, changed nothing. Now:
- the long roll plays its own files (`Animations\TKDodge\LongRoll<Dir>.hkx`, about 614 forward);
- Shorter installs shortened copies of every step and roll clip as well as shortened motion data, first person included;
- every clip's own motion equals its motion data, so distances are the same with AMR and without it. With AMR the
  standard back and side rolls now go 300 / 251 (they went 202 / 210 before).
- first person: the standard roll plays with no long-roll warning;
- chain off: a press during a step that the step outlasts is dropped once (one "Already dodging" line).

## Setup
1. Njordlinger, profile **Njordlinger Test**. Reinstall **test Simple Dodge 1.2.0** from this package. FOMOD:
   Line-SE-AE16, step distance **Normal**, Compatibility default (Bow Rapid Combo V3 keeps its bow dodges) except where
   B1 says otherwise. Keep **test Simple Dodge 1.1.0**, **test TK Dodge AIO 1.1.0** and **unpublished TK Dodge AIO**
   disabled. Animation Motion Revolution stays ENABLED unless a step says to hide it.
2. Behaviour regeneration (the patch changed - the long roll clip generators point at new files):
   - `py -3 "D:\Claude output\.MD\scripts\gates\pandora-active-patches-gate.py" --fix`, then pandora-run (`--auto_run
     --auto_close`), output mod **Pandora Output**.
   - Check: Engine.log has no "ERROR : Packfile > ... FAILED" or "Enum dose not contain" line; 1hm_behavior, mt_behavior
     and magicbehavior .hkx contain "SimpleDodgeState" and "LongRollForward"; `Characters\DefaultMale.hkx` contains
     "LongRollForward.hkx". Stop before launching if any is missing.
3. `uLogLevel = 1`; watch `Simple Dodge.log`. Raise CarryWeight before adding items; noon; flat floor (Dragonsreach hall
   carpet, as round 2). "Moved" includes the ~0.1 s walk from the held movement key, as in round 2.

## Checks (game state -> action -> EXPECTED)

### F5 - long roll distance (AMR enabled)
- `bStepDodge = false`, `bLongRoll = true`, sword drawn, third person: roll forward 3 times. Then `bLongRoll = false`,
  roll forward 3 times. EXPECTED: long roll about 614 (+ walk, so about 660-680), standard about 409 (+ walk, about 465
  as round 2). The long roll clearly further.
- One long roll Back with step dodge off is not needed (every roll is the forward roll).

### P2 - Shorter (AMR enabled, then hidden)
- **P2a** Reinstall choosing **Shorter**, run Pandora again (setup 2), relaunch. Step dodge on, flat floor, third person
  and first person, F / B / L / R. EXPECTED about 287 / 180 / 201 / 201 (+ walk), against round 2's Normal 454 / 318 /
  260 / 261 (third) and 425 / 313 / 266 / 266 (first). Long roll forward still about 614 (+ walk); standard roll
  forward about 287 (+ walk) third person, and first person about 287 too.
- **P2b** Without AMR: hide **Animation Motion Revolution** in the profile (untick it; Pandora need not run again),
  relaunch, repeat P2a's third-person F / B / L / R and the long roll forward. EXPECTED the same distances as P2a
  (within about 10). Re-enable AMR afterwards.
- **P2c** (still without AMR, Normal reinstalled, Pandora again) one forward long roll and one forward standard roll.
  EXPECTED about 614 and 409 (+ walk) - the same as with AMR. Re-enable AMR and put the step distance back to Normal at
  the end (rerun Pandora).

### F4 - first person, long roll on
- First person, drawn, `bStepDodge = false`, `bLongRoll = true`, roll in 4 directions. EXPECTED: the turn + forward roll
  as round 2, "Dodge: first person has no long roll - the standard roll plays" at debug level, and NO warning line
  "Long roll is on but this character's behaviour has no long roll".

### C4 - chain off, press during the step
- `bChainStepToRoll = false`, `bStepDodge = true`, step left, press dodge again at about 40% of the step. EXPECTED: no
  roll, one stamina charge, and exactly ONE "Dodge failed because of: Already dodging" line for that press (round 2: 23).
- Then press again in the last 0.3 s of a step. EXPECTED: a second step starts right after the first lands (the
  press is kept, because the step ends inside the 0.4 s buffer).

### T1 - sword near the thigh (freecam side view)
- Iron sword drawn (left hand empty), step dodge Forward-Right. Use a freecam side view (`tfc`, place the camera at the
  player's right side, about 150 units away, at hip height; or the camera tool the harness has) and save frames around
  the landing (clip frame 11 of 22, about 0.35 s after the press). EXPECTED: the blade passes beside the right thigh,
  not through it (the offline check measured 5.1 units between the blade axis and the thigh bone at that frame).

### S1 - dodge while sprinting (bDodgeWhileSprinting = true, the default)
- Sprint (hold the sprint key, or the dodge key if it is not the sprint key), then press dodge / double-tap a direction.
  EXPECTED: a dodge plays out of the sprint. Log "Dodge: out of a sprint - dodged" (or "(SprintStop sent first)"); no
  "Actor is sprinting" line. If the log says "the graph took no dodge", the sprint state needs its own transition: say so.
- Sprint attack (vanilla sprint power attack, and BFCO/MCO's if installed), press dodge after the hit.
  EXPECTED: the dodge cancels the attack's recovery.
- bDodgeWhileSprinting = false: EXPECTED "Dodge failed because of: Actor is sprinting", once per press.

### Regression (quick, AMR enabled, Normal)
- **B1** Installer option "Use Simple Dodge's bow steps over Bow Rapid Combo V3": bow drawn, back step. EXPECTED
  grounded bow step, about 318 (+ walk).
- **C1** Chain on: step left, forward + press at about 50%. EXPECTED "Chain: step -> long roll (iStep 4)", and the
  roll now travels the long roll's distance.
- **F1** Step off, long roll on, drawn: roll Left and Back. EXPECTED: turn + forward long roll each time.
