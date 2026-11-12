Simple Dodge
Version 1.0.0

WHAT IT IS
An SKSE dodge for Skyrim SE 1.5.97, AE 1.6.1170 and Skyrim 1.7.x. Tap Sprint (or a dodge key, or Sneak) with a direction held and your character steps out of the way: a weighted step with the guard up, or a roll if you prefer. Eight directions, dodge in place, double tap if you want it (of the dodge key, or of a direction), a long roll, a stamina cost (flat or a share of max stamina), invincibility frames, attack cancel (light attacks only if you like, or only in the MCO/BFCO recovery window), dodge while sneaking, dodge with weapons sheathed (off by default), no stamina regen during a dodge and a dodge sound (both off by default), a shorter step distance to pick in the installer, chaining a step into a roll (off by default), rolls that turn to the stick direction, an optional perk lock and an on-dodge spell. Its own step dodges, diagonals, rolls and an open-hand unarmed set are included. Settings are on a menu page and in Simple Dodge.ini, in eleven languages.

REQUIREMENTS
- SKSE (SKSE 2.3.x for Skyrim 1.7.x)
- Address Library for SKSE Plugins (All-in-One v13 or newer for Skyrim 1.7.x)
- Pandora Behaviour Engine or Nemesis, run after installing with "Simple Dodge" ticked

OPTIONAL
- SKSE Menu Framework (or the Apocrypha Menu Framework) for the settings page; without it the INI is read at start.
- Open Animation Replacer, for the unarmed set (used while both hands are empty, and for dodges with weapons sheathed).
- IFrame Generator RE, for invincibility frames during the dodge.
- Perk Entry Point Extender, so perks can change the dodge cost and invincibility time.
- Behavior Data Injector, for the 'Only in the MCO/BFCO recovery window' option.

COMPATIBILITY
- Dodge animation packs: Simple Dodge uses TK Dodge's file names, folder and dodge events, so step-dodge and roll packs made for TK Dodge replace its animations (install the pack after Simple Dodge). Step dodges: meshes\actors\character\animations\TKDodge\StepDodgeForward/Back/Left/Right.hkx. Rolls: animations\dodgeback.hkx, dodgeleft.hkx, dodgeright.hkx, sneakrun_forwardroll.hkx (forward). Since 1.2.0 every roll is the forward roll (sneakrun_forwardroll.hkx), played after the body turns to the stick direction, so a pack's back, left and right roll clips are no longer played; Simple Dodge still ships its own, so a pack's files still have a place. Diagonals (Simple Dodge's own): TKDodge\StepDodgeForwardLeft/ForwardRight/BackLeft/BackRight.hkx - switch Eight-way dodging off to use only a four-way pack's clips. Events: TKDodgeForward/Back/Left/Right (+ the four diagonal events). The unarmed set is an OAR submod at priority 100; an OAR pack with a higher priority wins.
- Combat mods: tested with MCO and with BFCO (use one of the two). Run Pandora or Nemesis with the combat mod and Simple Dodge both ticked. 'Only in the MCO/BFCO recovery window' lets a dodge cancel an attack only once the combat mod opens its window for the next move (MCO_WinOpen / BFCO_NextWinStart and their power-attack versions) and needs Behavior Data Injector; with 'Only cancel light attacks' on, that rule is used instead.
- Improved Camera: works (reported by a player, 2026-11-12).
- Other dodge mods: use Simple Dodge instead of TK Dodge RE, TK Dodge NG or TK Dodge AIO, not beside them - two would fire every dodge twice. Untick TK Dodge's own behaviour patch in Pandora or Nemesis and run it again.

INSTALL
Install with your mod manager, pick your Skyrim version in the installer (SE / AE, or Skyrim 1.7.x), then run Pandora or Nemesis.

SETTINGS
Journal > System > Mod Control Panel > Simple Dodge, or edit Data\SKSE\Plugins\Simple Dodge.ini. Changes on the page apply at once; Save keeps them.

LOG
Documents\My Games\Skyrim Special Edition\SKSE\Simple Dodge.log, at info by default (uLogLevel=2). For a bug report set uLogLevel=0 (trace) and reproduce: the log then gives one line per hook with its address at start, and the reason whenever a dodge is refused.

LICENCE
GPL-3.0-or-later (LICENSE-SimpleDodge-GPL-3.0.txt). NOTICE.md and THIRD_PARTY_NOTICES.md carry every notice.

CREDIT
Simple Dodge is based on code by Styyx (GPL-3.0) and by Maxsu, Loop and FBplus (MIT); the behaviour patch includes work by Xingda666 and ThorKirienko, and the original dodge design is by tktk. Full credit, with links, is in NOTICE.md.
