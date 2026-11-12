# Simple Dodge 1.2.0 - in-game test steps

Package: `D:\Claude output\7. current test builds\Skyrim - Simple Dodge\Simple Dodge 1.2.0` (FOMOD).

## Setup (profile needs)

1. In the Njordlinger instance, profile **Njordlinger Test**:
   - Install the package as the MO2 mod **test Simple Dodge 1.2.0**. Installer choices:
     - game line **Skyrim SE 1.5.97 or AE 1.6.1170** (the Line-SE-AE16 DLL; use Line-17 only on 1.7.x);
     - step distance **Normal**.
   - Disable **test Simple Dodge 1.1.0**.
   - Keep **test TK Dodge AIO 1.1.0** and **unpublished TK Dodge AIO** DISABLED. Two dodge mods would fire every dodge twice, and their AVG toml defines the cost actor values.
   - Open Animation Replacer, IFrame Generator RE and the Apocrypha Menu Framework stay enabled.
2. **Behaviour regeneration (Pandora), required before launch.** Pandora reads the new mt_behavior patch, so this step cannot be skipped.
   - Run gate `pandora-active-patches-gate --fix` (role `pandora-active-patches-gate`). It marks Simple Dodge (code `sdge`) active in `Pandora Output\Pandora_Engine\ActiveMods.json`.
   - Launch **Pandora Behaviour Engine+.exe** THROUGH MO2, from the mod `Pandora Behaviour Engine Plus`, as the MO2 executable "Pandora" (or `--auto_run --auto_close`).
   - Output goes to the MO2 mod **Pandora Output**.
   - Check the Pandora log lists "Simple Dodge". Check that `Pandora Output\meshes\actors\character\behaviors\mt_behavior.hkx` has a new timestamp and contains "SimpleDodgeState".
3. INI: `Data\SKSE\Plugins\Simple Dodge.ini` (the package copy). Change values on the settings page (Mod Control Panel > Simple Dodge) or in the INI, then press Reload from INI.
   - Set `uLogLevel = 1` (debug) for the run.
   - The defaults are the 1.1.0 behaviour. Each check below names the switches it needs.
4. Watch the log live: `Documents\My Games\Skyrim Special Edition\SKSE\Simple Dodge.log`.

## Checks (each: game state needed -> action -> EXPECTED)

### Logs and plugin
- **A1** At game start, with Perk Entry Point Extender NOT installed -> read the log.
  EXPECTED: exactly one info line "Perk Entry Point Extender is not installed (it is optional) ...". No "critical" line.
- **A2** Any dodge -> log. EXPECTED: no "PerkEntryPointExtender.dll not found" lines, ever.

### Stamina (never recorded before)
- **S1** Weapon drawn, full stamina, `bUsePercentageCost = true`, `fDodgeCost = 15`.
  Action: read stamina through TestBench (actor value Stamina), dodge once, read it again after 0.2 s.
  EXPECTED: stamina drops by 15% of the player's max stamina (log "Dodge cost N applied to <player>").
- **S2** An NPC that dodges (if any) near the player. EXPECTED: the player's stamina does not drop on the NPC's dodge.
- **S3** `bNoStaminaRegenDuringDodge = true`. Dodge at about 50% stamina.
  EXPECTED: stamina does not rise between dodge start and end (sample through TestBench every 0.1 s), then refills.
  "No Stamina Regen" does not appear in Active Effects.
- **S4** Same with `bNoStaminaRegenDuringDodge = false`. EXPECTED: stamina regen during the dodge as before.

### Sheathed dodge
- **D1** `bDodgeWhenSheathed = false` (default), weapon SHEATHED, third person. Dodge in 4 directions.
  EXPECTED: no dodge, no stamina spent, one debug line per press: "Dodge failed because of: Weapon is sheathed and bDodgeWhenSheathed is off".
- **D2** `bDodgeWhenSheathed = true`, weapon SHEATHED, a sword equipped. Dodge in all 8 directions (step dodge on).
  EXPECTED: each direction plays the grounded step with OPEN HANDS (the Unarmed OAR set), the sword stays on the hip, and the character returns to normal movement afterwards.
- **D3** Same, `bStepDodge = false` (rolls). EXPECTED: rolls play while sheathed.
- **D4** Same as D2, FIRST PERSON, sheathed. EXPECTED: forward, back, left and right dodges play in first person.
- **D5** Sitting in a chair, sheathed, setting on. EXPECTED: no dodge.

### Reworked step dodge (base, all 8 directions) - save frames
- **R1** Unarmed, fists drawn, third person, step dodge on, eight-way on. Dodge Forward, Back, Left, Right, Forward-Left, Forward-Right, Back-Left, Back-Right. Save frames of each (gamevideo or frame capture).
  EXPECTED for each:
  - one foot always on the ground (no hop) and the body never rises above standing height;
  - the trunk leans clearly into the dodge direction;
  - on landing the lead knee bends deeply, pointing in toward the body, and the trunk rocks back a little before settling;
  - no foot pop at the start or end.

### Weapon-type sets (equip, dodge in 4 directions, drawn vs sheathed)
For EACH of: sword (and war axe or mace) alone; sword + torch; sword + shield; dagger; two swords (dual wield); greatsword; battleaxe; warhammer; bow; crossbow; staff; a spell in the right hand; a spell in the left hand only; spells in both hands.
- **W1** Weapon DRAWN. Step dodge Forward, Back, Left, Right.
  EXPECTED: the arms hold that type's combat grip through the step and the weapon moves with the body (bow, staff and battleaxe as in the review MP4s). Nothing passes through the legs or torso at the lean or the landing crouch.
- **W2** Same weapon SHEATHED (`bDodgeWhenSheathed = true`). EXPECTED: the open-hand Unarmed step plays, not the grip.
- **W3** OAR editor (in-game OAR menu), Simple Dodge. EXPECTED: 12 submods (Unarmed 100, OneHanded 110 ... MagicBoth 120), no entries in Detected Problems.

### Shorter step option (needs a Pandora run each)
- **P1** Installed with step distance **Normal**, Pandora run. Step dodge forward, back and left once each, standing on a flat floor beside a marker.
  EXPECTED distances: forward about 409 units, back 300, sides about 251.
- **P2** Reinstall `test Simple Dodge 1.2.0` choosing step distance **Shorter**, run Pandora again (step 2), relaunch. Repeat P1.
  EXPECTED: forward about 287, back 180, sides about 201. The long roll is unchanged. The standard roll (long roll off) is shorter too. Watch for the feet sliding on landing; report it if seen.

### Other new settings
- **N1** `bDodgeSound = true`. Dodge. EXPECTED: a short whoosh (Skyrim.esm WPNSwingUnarmed) at each dodge start, following the player.
  With it false: silent.
- **N2** Change `fMenuExitGrace` to 1.0 in the INI, press Reload from INI, open and close the journal with the dodge key.
  EXPECTED: a dodge press within 1 s of closing is ignored. Press Save: the key is written to the INI.

### Not in this build (do not test)
- Chain a step into a roll (item 8).
- Rolls turning the body to the stick direction and always using the forward roll (item 9).
