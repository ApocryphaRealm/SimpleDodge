"""Long roll - a second, longer-travelling roll in the Simple Dodge behaviour patch (1.1.0, 2026-11-12).

Why: a player (Nexus posts, 2026-11-12): "for the roll dodge it makes more sense to cover more ground as you roll".
Without Animation Motion Revolution, Skyrim moves the character by the animationdatasinglefile MOTION DATA (with it,
by the clip's own animmotion annotations: since 1.2.0 the long roll has its own files, tools/make_clip_motion.py)
of the clip generator's NAME. Each direction's roll and step clip shared one name (TKDodgeLeft, ...), so the roll
went exactly as far as the step (251 / 300 / 409 units, TK Dodge RE's values). This script adds, per graph with a
dodge selector (1hm_behavior, magicbehavior):

  * four clip generators TKDodgeLongRoll<Dir>, cloned from the four roll clips (same .hkx, same triggers);
  * selector slots 4 and 5 on every dodge hkbManualSelectorGenerator (iStepSelector = iStep + iIsPlayer, so
    iStep 4 picks them; 0/1 stay the roll, 2/3 the step), with the long roll of that selector's direction;
  * the graph variable iSDGLongRoll (INT32, initial 1). The DLL only sets iStep 4 when the graph answers
    iSDGLongRoll == 1, so a player who updates without re-running Nemesis/Pandora keeps the old roll instead of
    pushing the selector past its last generator.

and, in animationdatasinglefile DefaultMale~1 / DefaultFemale~1, four motion entries sdge$8..sdge$11: the roll's
own motion (the step entry it used to share) times LONG_ROLL_SCALE, same key times and duration.

Idempotent: a second run finds iSDGLongRoll and changes nothing. Keeps each file's CRLF + tab layout.
Usage: python patch_longroll.py [<path to Nemesis_Engine\\mod\\sdge>]   (default: the repo's dist copy)
"""
import os, re, sys

LONG_ROLL_SCALE = 1.5
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(os.path.dirname(HERE), "dist", "Nemesis_Engine", "mod", "sdge")
VAR = "iSDGLongRoll"
DIRS = ("Left", "Back", "Right", "Forward")
# motion entry each roll used to share (its step's), and the new entry
MOTION = {"Forward": ("sdge$0", "sdge$8"), "Back": ("sdge$1", "sdge$9"), "Left": ("sdge$2", "sdge$10"),
          "Right": ("sdge$3", "sdge$11")}
CLOSE = "<!-- CLOSE -->"


def rd(p):
    return open(p, "rb").read().decode("utf-8")


def wr(p, t):
    open(p, "wb").write(t.encode("utf-8"))


def node_files(folder):
    out = {}
    for f in os.listdir(folder):
        m = re.fullmatch(r"#sdge\$(\d+)\.txt", f)
        if m:
            out[int(m.group(1))] = os.path.join(folder, f)
    return out


def append_in_block(text, contains, insert, nl):
    """Insert `insert` before the CLOSE of the first sdge MOD_CODE block whose body contains `contains`."""
    pos = 0
    while True:
        o = text.find("<!-- MOD_CODE ~sdge~ OPEN -->", pos)
        if o < 0:
            raise RuntimeError("no sdge block containing %r" % contains)
        c = text.find(CLOSE, o)
        if contains in text[o:c]:
            return text[:c] + insert + nl + text[c:]
        pos = c


def patch_graph(folder, log):
    nodes = node_files(folder)
    strdata = vals = infos = None
    for f in os.listdir(folder):
        if not re.fullmatch(r"#\d{4}\.txt", f):
            continue
        t = rd(os.path.join(folder, f))
        if 'class="hkbBehaviorGraphStringData"' in t: strdata = os.path.join(folder, f)
        elif 'class="hkbVariableValueSet"' in t: vals = os.path.join(folder, f)
        elif 'class="hkbBehaviorGraphData"' in t: infos = os.path.join(folder, f)
    if VAR in rd(strdata):
        log.append("%s: already patched (%s present)" % (folder, VAR))
        return
    nl = "\r\n" if "\r\n" in rd(strdata) else "\n"
    # roll clips: the hkbClipGenerator whose animation is not under TKDodge\ and whose name is a cardinal event
    roll = {}
    for n, p in nodes.items():
        t = rd(p)
        if 'class="hkbClipGenerator"' not in t:
            continue
        name = re.search(r'<hkparam name="name">([^<]*)<', t).group(1)
        anim = re.search(r'<hkparam name="animationName">([^<]*)<', t).group(1)
        for d in DIRS:
            if name == "TKDodge" + d and "TKDodge\\" not in anim:
                roll[d] = (n, p)
    if sorted(roll) != sorted(DIRS):
        raise RuntimeError("%s: roll clips found for %s only" % (folder, sorted(roll)))
    nxt = max(nodes) + 1
    long_id = {}
    for d in DIRS:
        n, p = roll[d]
        t = rd(p)
        new = "#sdge$%d" % nxt
        t = t.replace('name="#sdge$%d"' % n, 'name="%s"' % new, 1)
        t = t.replace('<hkparam name="name">TKDodge%s<' % d, '<hkparam name="name">TKDodgeLongRoll%s<' % d, 1)
        wr(os.path.join(folder, "%s.txt" % new), t)
        long_id[n] = new
        log.append("%s: %s = TKDodgeLongRoll%s (clone of #sdge$%d)" % (folder, new, d, n))
        nxt += 1
    # selectors: [roll, roll, step, step] -> + [long, long]
    for n, p in sorted(nodes.items()):
        t = rd(p)
        if 'class="hkbManualSelectorGenerator"' not in t:
            continue
        m = re.search(r'(<hkparam name="generators" numelements=")4(">\s*)(#sdge\$(\d+)) (#sdge\$\d+) (#sdge\$\d+) (#sdge\$\d+)', t)
        if not m or int(m.group(4)) not in long_id:
            raise RuntimeError("%s: selector #sdge$%d is not [roll, roll, step, step]" % (folder, n))
        lg = long_id[int(m.group(4))]
        t = t[:m.start()] + m.group(1) + "6" + m.group(2) + " ".join(m.group(i) for i in (3, 5, 6, 7)) + " %s %s" % (lg, lg) + t[m.end():]
        wr(p, t)
        log.append("%s: selector #sdge$%d gets %s at slots 4 and 5" % (folder, n, lg))
    # the variable
    wr(strdata, append_in_block(rd(strdata), "<hkcstring>iStep</hkcstring>", "\t\t\t\t<hkcstring>%s</hkcstring>" % VAR, nl))
    v = "\t\t\t\t<hkobject>%s\t\t\t\t\t<hkparam name=\"value\">1</hkparam>%s\t\t\t\t</hkobject>" % (nl, nl)
    wr(vals, append_in_block(rd(vals), '<hkparam name="value">', v, nl))
    info = ("\t\t\t\t<hkobject>{n}\t\t\t\t\t<hkparam name=\"role\">{n}\t\t\t\t\t\t<hkobject>{n}"
            "\t\t\t\t\t\t\t<hkparam name=\"role\">ROLE_DEFAULT</hkparam>{n}\t\t\t\t\t\t\t<hkparam name=\"flags\">0</hkparam>{n}"
            "\t\t\t\t\t\t</hkobject>{n}\t\t\t\t\t</hkparam>{n}\t\t\t\t\t<hkparam name=\"type\">VARIABLE_TYPE_INT32</hkparam>{n}"
            "\t\t\t\t</hkobject>").format(n=nl)
    wr(infos, append_in_block(rd(infos), "VARIABLE_TYPE_", info, nl))
    log.append("%s: variable %s added (names, values = 1, infos INT32)" % (folder, VAR))


def patch_animdata(project, log):
    for d in DIRS:
        src, dst = MOTION[d]
        clip = os.path.join(project, "TKDodgeLongRoll%s~%s.txt" % (d, dst))
        motion = os.path.join(project, "%s.txt" % dst)
        if os.path.exists(clip) and os.path.exists(motion):
            continue
        t = rd(os.path.join(project, "%s.txt" % src))
        nl = "\r\n" if "\r\n" in t else "\n"
        lines = t.split(nl)
        assert lines[0] == src, (project, src, lines[0])
        count = int(lines[2])
        out = [dst, lines[1], lines[2]]
        for k in range(3, 3 + count):
            parts = lines[k].split(" ")
            tm, x, y, z = parts[0], float(parts[1]), float(parts[2]), parts[3]
            out.append("%s %s %s %s" % (tm, "%.1f" % (x * LONG_ROLL_SCALE) if abs(x) > 1e-3 else "0",
                                        "%.1f" % (y * LONG_ROLL_SCALE) if abs(y) > 1e-3 else "0", "0"))
        out += lines[3 + count:]
        wr(motion, nl.join(out))
        ct = rd(os.path.join(project, "TKDodge%s~%s.txt" % (d, src)))
        cl = ct.split(nl)
        cl[0], cl[1] = "TKDodgeLongRoll%s" % d, dst
        wr(clip, nl.join(cl))
        log.append("%s: TKDodgeLongRoll%s -> %s (%s x %.1f)" % (project, d, dst, src, LONG_ROLL_SCALE))


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    log = []
    for g in ("1hm_behavior", "magicbehavior"):
        patch_graph(os.path.join(root, g), log)
    for pr in ("DefaultMale~1", "DefaultFemale~1"):
        patch_animdata(os.path.join(root, "animationdatasinglefile", pr), log)
    print("\n".join(log) if log else "nothing to do")


if __name__ == "__main__":
    main()
