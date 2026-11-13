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
BRC_OVERRIDE_PRIORITY = 9901700
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

# Keyword sets for the Animated Armoury / Heavy Armory weapon types (the owner, 2026-11-12). Conditioned on the weapon's
# KEYWORD, so a pike uses the pike set rather than the greatsword set it would get by its vanilla type; priorities
# 131-154, above the vanilla-type sets (110-120). ONE SOURCE PLUGIN PER SUBMOD: a keyword whose plugin is not loaded does
# not resolve, OAR marks that condition invalid and the submod never plays - kept per source, a missing mod costs only
# its own submod, never another source's. Heavy Armory's and OCF's keywords are injected into Update.esm's id range
# (their FormIDs carry Update.esm's index), so they are looked up as Update.esm forms; OCF (Object Categorization
# Framework) keywords are shared by every mod that uses OCF.
def kw(plugin, fid, left=False):
    return {"condition": "IsEquippedHasKeyword", "requiredVersion": "1.0.0.0",
            "Keyword": {"pluginName": plugin, "formID": fid}, "Left hand": left}

def any_kw(plugin, fids, left=False):
    return kw(plugin, fids[0], left) if len(fids) == 1 else \
        {"condition": "OR", "requiredVersion": "1.0.0.0", "Conditions": [kw(plugin, f, left) for f in fids]}

AA, UPD = "NewArmoury.esp", "Update.esm"
KEYWORD_SETS = [  # submod folder, clips (anim-src/weapons/<set>), priority, description, conditions
    ("Halberd (Animated Armoury)", "Halberd", 131, "Animated Armoury halberds (WeapTypeHalberd).", [any_kw(AA, ["E4580"])]),
    ("Pike (Animated Armoury)", "Pike", 132, "Animated Armoury pikes and spears (WeapTypePike, WeapTypeSpear).", [any_kw(AA, ["E457E", "E457F"])]),
    ("QtrStaff (Animated Armoury)", "QtrStaff", 133, "Animated Armoury quarterstaves (WeapTypeQtrStaff).", [any_kw(AA, ["E4581"])]),
    ("Rapier (Animated Armoury)", "Rapier", 134, "Animated Armoury rapiers (WeapTypeRapier).", [any_kw(AA, ["801"])]),
    ("Katana (Animated Armoury)", "Katana", 135, "Animated Armoury katanas (WeapTypeKatana).", [any_kw(AA, ["344733"])]),
    ("Claws (Animated Armoury)", "Claws", 136, "Animated Armoury claws in either hand (WeapTypeClaw).",
     [{"condition": "OR", "requiredVersion": "1.0.0.0", "Conditions": [kw(AA, "19AAB4"), kw(AA, "19AAB4", left=True)]}]),
    # Heavy Armory (141-143) and OCF (151-154) sets REMOVED 2026-11-13: those weapons carry a vanilla animation type
    # and stand in the vanilla two-handed (or one-handed) idle, so a set posed on Animated Armoury's stance turned the
    # weapon at the start and end of every dodge (the owner, playing, with a Spear of Skyrim spear: "The spear dodge
    # animation swaps the weapon direction unlike the vanilla weapons"). They now get the vanilla-type set of their
    # animation type, which holds the weapon exactly as that idle does.
]
REMOVED = ["Halberd (Heavy Armory)", "Pike (Heavy Armory)", "QtrStaff (Heavy Armory)", "Halberd (OCF)", "Pike (OCF)",
           "QtrStaff (OCF)", "Katana (OCF)"]


def write_keyword_sets():
    for folder in REMOVED:
        if os.path.isdir(os.path.join(OAR, folder)):
            shutil.rmtree(os.path.join(OAR, folder)); print("removed %s" % folder)
    for folder, clips, prio, desc, conds in KEYWORD_SETS:
        dst = os.path.join(OAR, folder)
        os.makedirs(os.path.join(dst, "TKDodge"), exist_ok=True)
        for d in DIRS:
            src = os.path.join(SRC, clips, "StepDodge%s.hkx" % d)
            if not os.path.isfile(src):
                raise SystemExit("missing %s - build it first (build_stepdodge.py -- build verify %s%s)" % (src, d, clips))
            shutil.copyfile(src, os.path.join(dst, "TKDodge", "StepDodge%s.hkx" % d))
        cfg = {"name": folder, "description": "Step dodges holding the weapon: " + desc +
               " Only while the weapon is drawn. Rolls are not replaced. Never plays if that mod is not installed.",
               "priority": prio, "conditions": [DRAWN] + conds}
        open(os.path.join(dst, "config.json"), "w", newline="\r\n").write(json.dumps(cfg, indent=4) + "\n")
        print("%-28s %d  8 clips (%s)" % (folder, prio, clips))


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
        if folder == "Bow":
            # The installer's Compatibility option (the owner, 2026-11-12: "No rapid bow combo should win by default unless
            # they want ours to win in the installer"): an OAR user.json beside this config.json shadows it WHOLE, so it is
            # the same config with only the priority raised above Bow Rapid Combo V3 (Base 2 9901001, TK Dodge Rear
            # 9901661/9901662). Written here so it can never drift from the Bow config it shadows.
            u = dict(cfg); u["priority"] = BRC_OVERRIDE_PRIORITY
            u["description"] = cfg["description"] + " (Installer option: priority %d, above Bow Rapid Combo V3.)" % BRC_OVERRIDE_PRIORITY
            ud = os.path.join(REPO, "fomod-options", "Compat-BowRapidComboV3", "Meshes", "Actors", "Character", "animations",
                              "OpenAnimationReplacer", "Simple Dodge", "Bow")
            os.makedirs(ud, exist_ok=True)
            open(os.path.join(ud, "user.json"), "w", newline="\r\n").write(json.dumps(u, indent=4) + "\n")
            print("  + fomod-options Compat-BowRapidComboV3 user.json at priority %d" % BRC_OVERRIDE_PRIORITY)


if __name__ == "__main__":
    main()
    write_keyword_sets()
