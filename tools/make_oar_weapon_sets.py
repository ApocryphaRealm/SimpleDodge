"""Writes the per-weapon-type OAR submods of Simple Dodge (1.2.0, 2026-11-12) and copies their step-dodge clips in.

The owner: "now we need to add the weapon type anims for holding the weapons while dodging". Each submod replaces the
eight step dodges (TKDodge\\StepDodge<Dir>.hkx) with the same steps holding that weapon type's vanilla combat-idle grip
(anim-src/build_stepdodge.py, GRIPS). All of them need the weapon drawn (sheathed, the Unarmed set plays). Priorities
110-120: above the Unarmed set (100), below anything a player adds with a bigger number; all unique.
IsEquippedType values are OAR's own enum (open-animation-replacer reference section 5): 1 sword, 2 dagger, 3 war axe,
4 mace, 5 greatsword, 6 battleaxe, 7 bow, 8 staff, 9 crossbow, 10 warhammer, 11 shield, 12-16 spells, 17 scroll,
18 torch. Daggers use the one-handed grip (the game has no dagger combat idle of its own).
Usage: python make_oar_weapon_sets.py
"""
import json, os, shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "anim-src", "weapons")
OAR = os.path.join(REPO, "dist", "Meshes", "Actors", "Character", "animations", "OpenAnimationReplacer", "Simple Dodge")
DIRS = ["Left", "Right", "Forward", "Back", "ForwardLeft", "ForwardRight", "BackLeft", "BackRight"]
ONE_H = [1, 2, 3, 4]
SPELLS = [12, 13, 14, 15, 16, 17]


def eq(v, left=False):
    return {"condition": "IsEquippedType", "requiredVersion": "1.0.0.0", "Type": {"value": float(v)}, "Left hand": left}


def any_of(vals, left=False, negated=False):
    c = eq(vals[0], left) if len(vals) == 1 else \
        {"condition": "OR", "requiredVersion": "1.0.0.0", "Conditions": [eq(v, left) for v in vals]}
    if negated:
        c = dict(c); c["negated"] = True
    return c


DRAWN = {"condition": "IsWeaponDrawn", "requiredVersion": "1.0.0.0"}
SETS = [  # folder, priority, description, conditions (all ANDed, plus weapon drawn)
    ("OneHanded", 110, "Sword, war axe, mace or dagger in the right hand; the left hand empty or holding a torch.",
     [any_of(ONE_H), any_of(ONE_H + [11] + SPELLS, left=True, negated=True)]),
    ("OneHandedShield", 111, "A one-handed weapon or dagger in the right hand and a shield in the left.",
     [any_of(ONE_H), eq(11, left=True)]),
    ("DualWield", 112, "One-handed weapons or daggers in both hands.", [any_of(ONE_H), any_of(ONE_H, left=True)]),
    ("Greatsword", 113, "A greatsword.", [eq(5)]),
    ("BattleaxeWarhammer", 114, "A battleaxe or a warhammer (OAR tells them apart; both are listed).", [any_of([6, 10])]),
    ("Bow", 115, "A bow.", [eq(7)]),
    ("Crossbow", 116, "A crossbow.", [eq(9)]),
    ("Staff", 117, "A staff in the right hand.", [eq(8)]),
    ("MagicRight", 118, "A spell or scroll in the right hand only.", [any_of(SPELLS), any_of(SPELLS, left=True, negated=True)]),
    ("MagicLeft", 119, "A spell or scroll in the left hand and the right hand empty.", [any_of(SPELLS, left=True), eq(0)]),
    ("MagicBoth", 120, "Spells or scrolls in both hands.", [any_of(SPELLS), any_of(SPELLS, left=True)]),
]


def main():
    for folder, prio, desc, conds in SETS:
        dst = os.path.join(OAR, folder)
        os.makedirs(os.path.join(dst, "TKDodge"), exist_ok=True)
        for d in DIRS:
            src = os.path.join(SRC, folder, "StepDodge%s.hkx" % d)
            if not os.path.isfile(src):
                raise SystemExit("missing %s - build it first (build_stepdodge.py -- build verify %s%s)" % (src, d, folder))
            shutil.copyfile(src, os.path.join(dst, "TKDodge", "StepDodge%s.hkx" % d))
        cfg = {"name": folder, "description": "Step dodges holding the weapon: " + desc +
               " Only while the weapon is drawn. Rolls are not replaced.",
               "priority": prio, "conditions": [DRAWN] + conds}
        open(os.path.join(dst, "config.json"), "w", newline="\r\n").write(json.dumps(cfg, indent=4) + "\n")
        print("%-20s %d  8 clips" % (folder, prio))


if __name__ == "__main__":
    main()
