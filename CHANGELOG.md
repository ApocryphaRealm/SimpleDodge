# Changelog - Simple Dodge

## 1.2.0 - 2026-11-12 - untested

### Added
- Eight-way dodging in first person (a request from 1m0ws on Nexus): the four diagonal step dodges now have their own first-person animations in all three first-person behaviours (weapon drawn, weapons sheathed, magic). Before, a diagonal in first person played the straight forward or back dodge. Each diagonal sways and tilts the view along its own direction, built from the straight first-person dodges on either side of it, and travels the same distance as the third-person diagonal (with or without Animation Motion Revolution, and shortened by the installer's Shorter step distance). Needs Nemesis or Pandora run again.
- Dodge while sprinting (on by default; bDodgeWhileSprinting, a Nexus request): dodge from a sprint, and out of a sprint attack the same way other attacks can be dodged out of (bEnableDodgeAttackCancel, bUseMCORecoverWindow). Before, a dodge while sprinting was refused; turn the setting off for that.
- Step dodges for Animated Armoury, Heavy Armory and OCF-tagged weapons, picked by the weapon's keyword: halberds and glaives, pikes, spears and tridents, quarterstaves, rapiers, katanas and claws each hold their weapon through all eight directions. Each set only plays when its mod is installed.
- Installer page Compatibility: Bow Rapid Combo V3 keeps its own bow dodges by default (its back, left and right flips); choose 'Use Simple Dodge's bow steps over Bow Rapid Combo V3' to get Simple Dodge's bow steps in every direction.
- Chain a step into a roll (off by default; bChainStepToRoll, fChainWindowStart): press dodge again once the step has played past the window (40% by default) and it becomes a roll in the newly pressed direction, charged like any dodge. Once per chain - a roll never chains, a press before the window does nothing. Needs Nemesis or Pandora run again.
- Step dodges hold your weapon: eleven sets through Open Animation Replacer, each holding that weapon type's own combat grip through all eight directions - one-handed weapons and daggers (left hand empty or a torch), one-handed with a shield, dual wield, greatsword, battleaxe and warhammer, bow, crossbow, staff, and spells in the right, left or both hands. Used only with the weapon drawn; rolls are shared.
- Dodge sound (off by default; bDodgeSound): a short whoosh when your dodge starts. The sound is sDodgeSoundID in the INI, by default the game's bare-hand swing (Skyrim.esm WPNSwingUnarmed).
- No stamina regen during a dodge (off by default; bNoStaminaRegenDuringDodge). Stamina does not refill from the start of your dodge to its end, through a hidden effect in Simple Dodge.esp that lasts at most 3 seconds.
- Step distance in the installer: Normal, or Shorter (forward 70%, back 60%, sideways 80%, diagonals by the same mix - the distances of TK Dodge Shorter Step Distance), in third and first person, with or without Animation Motion Revolution. The standard roll shares the step distances, so it is shorter too; the long roll is unchanged. Run Nemesis or Pandora after installing.
- Dodge with weapons sheathed (off by default; on the settings page, or bDodgeWhenSheathed in the INI). The behaviour patch now puts every dodge - step dodges, rolls, long rolls and diagonals - into the weapons-away animations too, in third and first person, and the open-hand unarmed set plays while weapons are sheathed. With it off, a dodge with weapons sheathed is refused at once, before any stamina is spent. Needs Nemesis or Pandora run again.

### Fixed
- With Animation Motion Revolution installed, the long roll now goes half as far again as the standard roll, and the installer's Shorter step distance now shortens the steps. Animation Motion Revolution moves you by the motion stored in each animation file, not by the behaviour's motion data, and the long roll used the standard roll's file while Shorter changed only the motion data. The long roll now has its own files, Shorter installs shortened copies of every step and roll file, and each file's motion matches the motion data, so distances are the same with or without Animation Motion Revolution. With it, the standard roll's back and side rolls now go as far as without it (300 and 251 instead of 202 and 210).
- Shorter now also shortens first-person dodges.
- In first person, where the behaviour has no long roll, the standard roll plays without a warning in the log.
- With the step-to-roll chain off, a dodge press during a step is dropped once when the step will outlast the input buffer, instead of being refused and logged as 'Already dodging' on every frame. A press just before the step ends still dodges again as soon as it lands.
- Pike, quarterstaff and halberd step dodges: both hands now close on the shaft in every frame of every direction (before, the left hand missed it by up to 14 units and both grips were turned across it).
- A dodge refused for a reason that will not change in a moment (over carry weight, not enough stamina, no perk, weapon sheathed) is dropped at once instead of being retried and logged on every frame of the input buffer.
- An NPC's dodge no longer takes stamina from the player: only the player's own dodge start charges the player's stamina.
- fMenuExitGrace (how long a dodge press is ignored after a menu closes) is now read from and saved to the INI; it was always 0.25 s.
- A DodgeCostModifier or ExtraDodgeCostModifier actor value that reads 0 or less (defined by another mod's Actor Value Generator file, such as TK Dodge RE Addon's) no longer makes dodges free; it counts as 1, and the log says so once.
- Without Perk Entry Point Extender (it is optional), the log no longer prints a critical 'PerkEntryPointExtender.dll not found' line several times on every dodge press; it says once, at info level, that perks cannot change the dodge cost or invincibility time without it.

### Changed
- Every roll is now the forward roll: the body turns at once to the direction you push (stick or keys, relative to the camera, diagonals included) and rolls forward that way. Dodging in place rolls straight ahead. Step dodges keep their eight directional clips. The back, left and right roll clips stay in the package for roll packs but are no longer played.
- Step dodges are a heavy, grounded step instead of a hop: one foot stays on the floor the whole way (the lead foot skims no more than 2 units up, the push foot slides behind until the lead foot has landed), the body never rises above its stance, the trunk leans 20-26 degrees into the dodge, and it rocks back past upright as the lead knee takes the landing before settling.
- Step dodges reworked, all eight directions and the open-hand unarmed set: the body stays lower through the step, the trunk leans into the direction of the dodge and is upright again after landing, and the leg you land on arrives bent with its knee turned in toward the body, then sinks deeper to absorb the landing before rising back. Clip lengths, events and travel are unchanged.

## 1.1.0 - 2026-11-12 - untested

### Fixed
- A held sprint (or sneak) press is judged once, when it goes down: a press that outlasts the tap length reaches the game as a fresh press exactly once, so another mod that sets the sprint flag can no longer block the delayed sprint.
- Nemesis no longer stops with a critical error (Missing info in info.ini, Mod: sdge) when Simple Dodge is installed: the behaviour patch's info.ini now names its Nexus page (site=), which Nemesis requires. Pandora was never affected.
- Forty-two settings-page labels and help texts were English in every language; all eleven languages now carry them.
- A dodge key that is also the sprint or sneak key no longer counts one tap twice.
- With double-tap on, holding the sprint key (or a dodge key that is also the sprint key) no longer dodges. A double tap is now two short taps, each released within the tap length, the second within 0.3 s of the first; a held key never counts, whatever other sprint mods re-send while it is held.

### Added
- Double-tap a direction to dodge (off by default): tap a movement key, or flick the left stick, twice quickly to dodge that way.
- Long roll (on by default): rolls travel half as far again as a step dodge (step dodge off). Rolls used to share the step's motion, so they went no further. Needs Nemesis or Pandora run again; without that the standard roll plays.

## 1.0.0 - first release

### Dodging
- An SKSE dodge for Skyrim SE 1.5.97 and AE 1.6.1170, with a second build for Skyrim 1.7.x (1.7.99 / 1.7.104; needs
  SKSE 2.3.x and Address Library All-in-One v13 or newer). The installer asks which Skyrim you have.
- Step dodges (a weighted step with the guard up, one foot leading, the push foot landing second) or rolls, chosen in
  the settings; step dodge is on by default.
- Eight-way dodging: four diagonal step dodges, chosen from eight 45-degree directions (on by default; off gives the
  four main directions).
- An open-hand unarmed set of step dodges and rolls through Open Animation Replacer, used while both hands are empty.
- Dodge in place with a chosen default direction, an option to block the forward dodge, and a first-person-only option.
- Triggers: a tap of Sprint (on by default, 0.30 s tap window, so holding Sprint still sprints), a tap of Sneak, or a
  dodge key on keyboard, mouse or controller; optional double tap; input buffering.
- Stamina cost, flat or a percentage of max stamina (15% by default), with Actor Value Generator and Perk Entry Point
  Extender modifiers; invincibility-frame duration.
- Attack cancel, with light-attacks-only and 'Only in the MCO/BFCO recovery window' options (follows MCO's and BFCO's
  own windows: BFCO_NextWinStart / BFCO_NextPowerWinStart open it, a new swing closes it).
- Our own light plugin Simple Dodge.esp: the 'Dodge' perk (for the optional perk lock), the 'Dodge Spell' perk and the
  on-dodge spell 'Dodge Guard' (a brief Fortify Armor Rating).
- No dodge out of a menu: a tap whose press began in a menu, or a release whose press the plugin never saw, is refused,
  for the dodge key and the Sprint and Sneak taps alike.

### Settings and logging
- Settings page on the SKSE Menu Framework / Apocrypha Menu Framework, listed as Simple Dodge, in eleven languages:
  on/off switches, precise sliders (one unit of the shown digit per arrow-key or D-pad press), dodge-key capture.
- Settings in Data\SKSE\Plugins\Simple Dodge.ini.
- Log at Documents\My Games\Skyrim Special Edition\SKSE\Simple Dodge.log: one line per hook with its address, the
  reason whenever a dodge is refused, and a single clear line when the dodge behaviour is missing from the animation
  graph (run Pandora or Nemesis).
- A missing Address Library file, or the wrong build for your game, is named plainly in the log and on screen and the
  plugin loads inert.

### Compatibility
- Behaviour patch with its own patch code (`sdge`) for Pandora and Nemesis; the dodge events, graph variables and clip
  names follow the long-standing step-dodge layout, so step-dodge and roll replacer packs still replace our clips.
- Ships the Behavior Data Injector file that declares DodgeCancelEnabled for the recovery-window option.
