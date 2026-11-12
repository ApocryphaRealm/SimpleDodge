# Simple Dodge - copyright and licence

Simple Dodge is licensed under the **GNU General Public License, version 3 or (at your option) any later version**
(`LICENSE`). Copyright (C) 2026 ApocryphaRealm for the SE port, the Simple Dodge additions and the Apocrypha Menu
Framework settings page.

## What Simple Dodge is based on

Simple Dodge is based on TK Dodge AIO / TK Dodge RE Addon by Styyx (GPL-3.0), which is itself based on TK Dodge RE by
Maxsu, Loop and FBplus (MIT). Their copyright and credit are kept in full below.

| Part | Author | Licence | Source |
|---|---|---|---|
| TK Dodge RE Addon (dodge logic, input buffering, double tap, perk lock, on-dodge spell, stamina cost options, attack-cancel tuning) | Styyx | GPL-3.0 | https://github.com/Styyx1/TKDodgeAddon |
| TK Dodge RE (the script-free dodge the Addon grew from, and its behaviour patch) | Maxsu, FBplus, Loop, Xing | MIT | https://github.com/max-su-2019/TK-Dodge-RE |
| TK Dodge SE (the original dodge design, event names and clip layout) | tktk | see its Nexus page | https://www.nexusmods.com/skyrimspecialedition/mods/15309 |
| StyyxUtils helpers (form-string lookup, mod-loaded check, menu check, ApplySpell) - rewritten in `src/Compat.h` | Styyx (ApplySpell credited to KernalsEgg / colinswrath) | GPL-3.0 | https://github.com/Styyx1/StyyxUtils |
| Perk Entry Point Extender API header | NoahBoddie | see `src/API` | https://www.nexusmods.com/skyrimspecialedition/mods/91192 |

## Statement of changes

- Ported from xmake and an AE-only CommonLib fork to CMake + vcpkg **CommonLibSSE-NG**, so it runs on Skyrim SE 1.5.97
  and AE, with a second build line for Skyrim 1.7.x (CommonLibSSE-NG 7.2.0).
- Hooks rewritten onto `write_vfunc` and the SKSE trampoline; the main-loop call site mapped to SE (id 35565 + 0x731 /
  AE id 36564 + 0xC26) and byte-checked before it is patched.
- Settings moved from REX::TOML to `Simple Dodge.ini` (same key names), read and written with plain file I/O.
- The settings page is drawn on the Apocrypha Menu Framework: on/off switches, translation keys, AMF reserved keys
  refused at key capture.
- Info logging by default (uLogLevel=0 for everything) with a level header; one log line per hook with its address; null checks on every lookup.
- New step dodges, diagonal step dodges, rolls and an unarmed set of our own; our own light plugin `Simple Dodge.esp`.
- The behaviour patch runs under its own patch code `sdge`; the dodge event, variable and clip names are kept so other
  dodge animation packs still line up.

See `THIRD_PARTY_NOTICES.md` for the bundled libraries and assets.
