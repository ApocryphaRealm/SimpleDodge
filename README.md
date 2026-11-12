# Simple Dodge

An SKSE dodge for Skyrim SE 1.5.97, AE 1.6.1170 and Skyrim 1.7.x. Tap Sprint, Sneak or a dodge key with a direction
held to step out of the way - a weighted step with the guard up, or a roll - in up to eight directions. Stamina cost,
invincibility frames, attack cancel (with an MCO/BFCO recovery-window option), an optional perk lock and on-dodge
spell, its own step dodges, diagonals, rolls and an unarmed set, and a settings page in eleven languages.

## Requirements

- SKSE and Address Library for SKSE Plugins
- Pandora Behaviour Engine or Nemesis, run after installing
- Optional: SKSE Menu Framework (settings page), Open Animation Replacer (unarmed set), IFrame Generator RE,
  Behavior Data Injector (MCO/BFCO recovery-window option), Perk Entry Point Extender, so perks can change the dodge
  cost and invincibility time

## Building

Needs Visual Studio 2022 with the C++ toolset and `VCPKG_ROOT` pointing at a vcpkg checkout.
Clone with `git clone --recursive` (or run `git submodule update --init`) for `extern/clib-util`.

- SE / AE: `configure.bat`, then `build.bat` - output in `build/relwithdebinfo-se-only/SimpleDodge.dll`
- Skyrim 1.7.x: `configure17.bat`, then `build17.bat` - output in `build/relwithdebinfo-17/SimpleDodge.dll`

The game files (behaviour patch, animations, plugin, translations, INI) are in `dist/`. Animation sources and the
Blender build scripts are in `anim-src/`.

## Licence

GPL-3.0-or-later with a modding exception - see `LICENSE`, `EXCEPTIONS`, `NOTICE.md` and `THIRD_PARTY_NOTICES.md`.

## Credit

Simple Dodge is based on code by Styyx (GPL-3.0) and by Maxsu, Loop and FBplus (MIT); the behaviour patch includes
work by Xingda666 and ThorKirienko, and the original dodge design is by tktk. Full credit, with links, is in
`NOTICE.md`.
