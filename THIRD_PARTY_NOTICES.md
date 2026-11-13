# Third-party notices

Simple Dodge is based on TK Dodge AIO / TK Dodge RE Addon by Styyx and on TK Dodge RE by Maxsu, Loop and FBplus.

| Component | Use | Licence |
|---|---|---|
| TK Dodge RE Addon (Styyx) | the code Simple Dodge is based on | GPL-3.0 (`LICENSE`) |
| TK Dodge RE (max-su-2019 - Maxsu, Loop, FBplus, Xing) | ancestor of the dodge logic and of the behaviour patch | MIT |
| StyyxUtils (Styyx) | helpers rewritten in `src/Compat.h` | GPL-3.0 |
| CommonLibSSE-NG (alandtse/CommonLibVR `ng`) | game and SKSE interfaces, statically linked | MIT |
| CLibUtil (powerof3) | key-name table (`extern/clib-util`) | MIT |
| spdlog / {fmt} | logging | MIT |
| DevBench API (alandtse) | `include/DevBench` | MIT (`include/DevBench/DevBenchAPI.LICENSE.txt`) |
| SKSE Menu Framework API header | `include/SKSEMenuFramework.h`, answered by the Apocrypha Menu Framework | see header |
| Perk Entry Point Extender API (NoahBoddie) | `src/API/PerkEntryPointExtenderAPI.h` | see header |
| True Directional Movement API (ersh1) | `src/API/TrueDirectionalMovementAPI.h` | GPL-3.0 (True Directional Movement); one change: GetModuleHandleA |

## Bundled game assets

The behaviour patch (`Nemesis_Engine/mod/sdge`) is based on TK Dodge RE's behaviour patch (Maxsu, Loop, FBplus), with
the TK Dodge Animation Pandora Patch (Xingda666, with tktk's permission) and the TK First Person Fix for Pandora
(ThorKirienko) merged in. The dodge event, variable and clip names come from TK Dodge SE (tktk). The step dodges, rolls,
unarmed set and `Simple Dodge.esp` are Simple Dodge's own. Each author is credited by name, with a link back to the
original mod page, in NOTICE.md, the README and the Credit section of the mod page.
