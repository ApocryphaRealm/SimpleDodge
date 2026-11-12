# Changelog - Simple Dodge

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
