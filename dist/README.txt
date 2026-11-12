Simple Dodge
Version 1.0.0

WHAT IT IS
An SKSE dodge for Skyrim SE 1.5.97, AE 1.6.1170 and Skyrim 1.7.x. Tap Sprint (or a dodge key, or Sneak) with a direction held and your character steps out of the way: a weighted step with the guard up, or a roll if you prefer. Eight directions, dodge in place, double tap if you want it, a stamina cost (flat or a share of max stamina), invincibility frames, attack cancel (light attacks only if you like, or only in the MCO/BFCO recovery window), dodge while sneaking, an optional perk lock and an on-dodge spell. Its own step dodges, diagonals, rolls and an open-hand unarmed set are included. Settings are on a menu page and in Simple Dodge.ini, in eleven languages.

REQUIREMENTS
- SKSE (SKSE 2.3.x for Skyrim 1.7.x)
- Address Library for SKSE Plugins (All-in-One v13 or newer for Skyrim 1.7.x)
- Pandora Behaviour Engine or Nemesis, run after installing with "Simple Dodge" ticked

OPTIONAL
- SKSE Menu Framework (or the Apocrypha Menu Framework) for the settings page; without it the INI is read at start.
- Open Animation Replacer, for the unarmed set (used while both hands are empty).
- IFrame Generator RE, for invincibility frames during the dodge.
- Behavior Data Injector, for the 'Only in the MCO/BFCO recovery window' option.

COMPATIBILITY
Step-dodge replacer packs made for TK Dodge replace Simple Dodge's step dodges and rolls: the clip names, folder and dodge events are the same. Use Simple Dodge instead of another dodge SKSE plugin, not beside one - two would fire every dodge twice.

INSTALL
Install with your mod manager, pick your Skyrim version in the installer (SE / AE, or Skyrim 1.7.x), then run Pandora or Nemesis.

SETTINGS
Journal > System > Mod Control Panel > Simple Dodge, or edit Data\SKSE\Plugins\Simple Dodge.ini. Changes on the page apply at once; Save keeps them.

LOG
Documents\My Games\Skyrim Special Edition\SKSE\Simple Dodge.log, at trace by default (uLogLevel=0). One line per hook with its address at start, and the reason whenever a dodge is refused.

LICENCE
GPL-3.0-or-later (LICENSE-SimpleDodge-GPL-3.0.txt). NOTICE.md and THIRD_PARTY_NOTICES.md carry every notice.

CREDIT
Simple Dodge is based on code by Styyx (GPL-3.0) and by Maxsu, Loop and FBplus (MIT); the behaviour patch includes work by Xingda666 and ThorKirienko, and the original dodge design is by tktk. Full credit, with links, is in NOTICE.md.
