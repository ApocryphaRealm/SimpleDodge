"""Make every dodge clip's own root motion agree with its motion data, so distances hold with or without Animation
Motion Revolution (AMR) - 1.2.0 round 3, 2026-11-13. See clip_motion.py for why: with AMR a clip's "animmotion"
annotations move the character and animationdatasinglefile is ignored.

Run after anything changes a clip or the motion data. Idempotent: each step sets values from the motion data, not
from the previous run.

  1. Standard rolls (dist): DodgeLeft / DodgeRight / DodgeBack / SneakRun_ForwardRoll.hkx share their clip
     generators' names - and so their motion data - with the steps (TKDodgeLeft = sdge$2, ...). Their annotations are
     scaled so the root reaches that motion data's end at its duration (back 300, sides 251.7 / 251.2, forward 409.3).
     Before, with AMR, the rolls went 202 / 210 / 210 / 409.
  2. Long rolls (dist): four new files Animations\\TKDodge\\LongRoll<Dir>.hkx, the standard roll scaled to the long
     roll's motion data (sdge$8..11, x1.5 of the standard). The TKDodgeLongRoll<Dir> clip generators of 1hm_behavior,
     mt_behavior and magicbehavior play them instead of the standard roll's file, and the character files
     (defaultmale / defaultfemale #0029) list them. Before, the long roll played the standard roll's file, so with
     AMR it went exactly as far.
  3. Shorter option (fomod-options\\Step-Shorter\\Meshes): a copy of every step clip (the base TKDodge set and every
     Open Animation Replacer set) and of the four standard rolls, each axis scaled like the Shorter motion data
     (forward x0.7, back x0.6, sideways x0.8; a diagonal's parts each by their own direction). The long rolls are
     not copied: they keep their length, as the option says.
Then checks every result with clip_motion.final against its motion data (the check the package gate also runs).
Usage: python make_clip_motion.py
"""
import glob, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import clip_motion as CM

REPO = os.path.dirname(HERE)
DIST = os.path.join(REPO, "dist")
ANIM = os.path.join(DIST, "Meshes", "Actors", "Character", "animations")
SDGE = os.path.join(DIST, "Nemesis_Engine", "mod", "sdge")
MD = os.path.join(SDGE, "animationdatasinglefile", "DefaultMale~1")
SHORT = os.path.join(REPO, "fomod-options", "Step-Shorter")
SHORT_ANIM = os.path.join(SHORT, "Meshes", "Actors", "Character", "animations")
FORWARD, BACK, SIDE = 0.7, 0.6, 0.8
# roll file, its standard motion entry, its long motion entry, the axis it travels on
ROLLS = {"Left": ("dodgeleft.hkx", "sdge$2", "sdge$10", 0), "Right": ("dodgeright.hkx", "sdge$3", "sdge$11", 0),
         "Back": ("dodgeback.hkx", "sdge$1", "sdge$9", 1), "Forward": ("sneakrun_forwardroll.hkx", "sdge$0", "sdge$8", 1)}
GRAPHS = ("1hm_behavior", "mt_behavior", "magicbehavior")


def motion(entry, folder=MD):
    """(duration, (x, y) at the end) of an animationdatasinglefile motion entry."""
    lines = open(os.path.join(folder, entry + ".txt"), encoding="ascii").read().split("\n")
    lines = [l.strip() for l in lines]
    dur, n = float(lines[1]), int(lines[2])
    t, x, y, z = lines[2 + n].split(" ")
    return dur, (float(x), float(y))


def scale_axis(src, dst, axis, target, duration):
    have = CM.final(src, duration)[axis]
    f = target / have
    CM.rewrite(src, dst, lambda x, y, z: (x * f, y, z) if axis == 0 else (x, y * f, z))
    return f


def shorter(x, y, z):
    return x * SIDE, y * (FORWARD if y > 0 else BACK), z


def main():
    report = []
    # 1 and 2, in the base folder and in every Open Animation Replacer set that has its own rolls (Unarmed): the set's
    # long roll is its own roll scaled, at the same path below the set (TKDodge\LongRoll<Dir>.hkx), so OAR swaps it too
    folders = [ANIM] + sorted({os.path.dirname(p) for p in glob.glob(os.path.join(ANIM, "OpenAnimationReplacer", "**",
                                                                                   "dodgeleft.hkx"), recursive=True)})
    for fo in folders:
        tag = os.path.relpath(fo, ANIM)
        for d, (f, std, lng, axis) in ROLLS.items():
            p = os.path.join(fo, f)
            if not os.path.isfile(p):
                continue
            dur, end = motion(std)
            k = scale_axis(p, p, axis, end[axis], dur)
            report.append("roll %-7s %s\\%s scaled x%.4f -> %.1f" % (d, tag, f, k, end[axis]))
            dur, end = motion(lng)
            k = scale_axis(p, os.path.join(fo, "TKDodge", "LongRoll%s.hkx" % d), axis, end[axis], dur)
            report.append("long roll %-7s %s\\TKDodge\\LongRoll%s.hkx x%.4f -> %.1f" % (d, tag, d, k, end[axis]))
    vanilla = {d: "Animations\\%s" % n for d, n in (("Left", "DodgeLeft.hkx"), ("Right", "DodgeRight.hkx"),
                                                    ("Back", "DodgeBack.hkx"), ("Forward", "SneakRun_ForwardRoll.hkx"))}
    changed = 0
    for g in GRAPHS:
        for p in glob.glob(os.path.join(SDGE, g, "*.txt")):
            t = open(p, "rb").read().decode("utf-8")
            m = re.search(r'<hkparam name="name">TKDodgeLongRoll(\w+)</hkparam>', t)
            if not m:
                continue
            d = m.group(1)
            new = 'name="animationName">Animations\\TKDodge\\LongRoll%s.hkx<' % d
            t2 = re.sub(r'name="animationName">[^<]*<', lambda _: new, t, count=1)
            if t2 != t:
                open(p, "wb").write(t2.encode("utf-8")); changed += 1
    report.append("long roll clip generators repointed: %d" % changed)
    for ch in ("defaultmale", "defaultfemale"):
        p = os.path.join(SDGE, ch, "#0029.txt")
        t = open(p, "rb").read().decode("utf-8")
        nl = "\r\n" if "\r\n" in t else "\n"
        anchor = "\t\t\t\t<hkcstring>Animations\\TKDodge\\StepDodgeBackRight.hkx</hkcstring>" + nl
        assert anchor in t, p
        add = "".join("\t\t\t\t<hkcstring>Animations\\TKDodge\\LongRoll%s.hkx</hkcstring>%s" % (d, nl)
                      for d in ("Forward", "Back", "Left", "Right") if "LongRoll%s.hkx" % d not in t)
        if add:
            t = t.replace(anchor, anchor + add, 1)
            open(p, "wb").write(t.encode("utf-8"))
        report.append("%s: long roll files listed" % ch)
    # 3. Shorter clips
    if os.path.isdir(os.path.join(SHORT, "Meshes")):
        shutil.rmtree(os.path.join(SHORT, "Meshes"))
    n = 0
    for p in glob.glob(os.path.join(ANIM, "**", "*.hkx"), recursive=True):
        rel = os.path.relpath(p, ANIM)
        base = os.path.basename(p).lower()
        if base.startswith("longroll"):
            continue
        if not (base.startswith("stepdodge") or base in [v[0] for v in ROLLS.values()]):
            raise SystemExit("unknown clip %s - decide whether Shorter scales it" % rel)
        CM.rewrite(p, os.path.join(SHORT_ANIM, rel), shorter); n += 1
    report.append("Shorter: %d clips" % n)
    print("\n".join(report))


if __name__ == "__main__":
    main()
