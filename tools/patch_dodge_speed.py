"""Dodge speed - the behaviour side (1.4.0, 2026-11-16; the owner: "build a faster version of Simple Dodge. Keep all of its
animation motions the way they are, just speed them up over the same distance").

Every dodge clip (steps, rolls, long rolls, diagonals; third and first person; drawn, magic and sheathed graphs) gets its
playbackSpeed bound to a graph variable the DLL sets before each dodge (fDodgeSpeed in Simple Dodge.ini):
  * SDG_DodgeSpeed         (float, default 1.0) - every clip whose own playbackSpeed is 1.0;
  * SDG_DodgeSpeedFwdStep  (float, default 0.9) - the forward step, which the patch has always played at 0.9.
The motion of a clip (the behaviour's motion data, or the clip's own annotations under Animation Motion Revolution) is
read by the clip's LOCAL time, so a faster playback covers the same distance in less time. Clip triggers (TKDodgeStop,
TKDR_DodgeEnd, the foot events) are in local time too and stay in step by themselves; the i-frame timer is graph time
(BSTimerModifier on TKDR_IframeDuration), so the DLL divides that duration by the speed.
The graph defaults equal the old static values, so a graph generated from this patch plays exactly as before until the
DLL sets something else, and an older DLL changes nothing.

Per graph this adds the two names to variableNames, their default words to wordVariableValues and VARIABLE_TYPE_REAL
entries to variableInfos (each in the patch's own appended MOD_CODE block), and one hkbVariableBindingSet node per clip.
Idempotent: a graph that already declares SDG_DodgeSpeed is left alone.
Usage: python patch_dodge_speed.py [<Nemesis_Engine\\mod\\sdge>]
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDGE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "dist", "Nemesis_Engine", "mod", "sdge")
GRAPHS = ["1hm_behavior", "magicbehavior", "mt_behavior",
          "_1stperson/1hm_behavior", "_1stperson/magicbehavior", "_1stperson/mt_behavior"]
VARS = [("SDG_DodgeSpeed", 1.0), ("SDG_DodgeSpeedFwdStep", 0.9)]
OPEN, CLOSE, ORIGINAL = "<!-- MOD_CODE ~sdge~ OPEN -->", "<!-- CLOSE -->", "<!-- ORIGINAL -->"


def rd(p):
    return open(p, "rb").read().decode("utf-8")


def wr(p, t):
    open(p, "wb").write(t.encode("utf-8"))


def files(folder):
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".txt")]


def by_class(folder, cls):
    out = [p for p in files(folder) if 'class="%s"' % cls in rd(p).split("\n", 1)[0]]
    assert len(out) == 1, (folder, cls, out)
    return out[0]


def word(f):
    return struct.unpack("<i", struct.pack("<f", f))[0]


def append_block(text, list_param):
    """(start, end) of the APPENDED sdge block inside <list_param> (the last one there without an ORIGINAL part)."""
    found = None
    for m in re.finditer(re.escape(OPEN), text):
        lists = re.findall(r'<hkparam name="(\w+)" numelements="\d+">', text[:m.start()])
        c = text.find(CLOSE, m.end())
        if lists and lists[-1] == list_param and ORIGINAL not in text[m.end():c]:
            found = (m.end(), c)
    if not found:
        raise RuntimeError("no appended sdge block in %s" % list_param)
    return found


def count_top(block):
    return len(re.findall(r"^\t\t\t\t<(?:hkobject|hkcstring)>", block, re.M))


def insert(text, list_param, rows, nl):
    s, c = append_block(text, list_param)
    return text[:c] + nl.join(rows) + nl + text[c:], count_top(text[s:c])


def patch(graph, log):
    folder = os.path.join(SDGE, *graph.split("/"))
    sd = by_class(folder, "hkbBehaviorGraphStringData")
    t = rd(sd)
    if "<hkcstring>SDG_DodgeSpeed</hkcstring>" in t:
        log.append("%s: already has SDG_DodgeSpeed" % graph)
        return
    nl = "\r\n" if "\r\n" in t else "\n"
    t, n_names = insert(t, "variableNames", ["\t\t\t\t<hkcstring>%s</hkcstring>" % v for v, _ in VARS], nl)
    vs = by_class(folder, "hkbVariableValueSet")
    u = rd(vs); nl2 = "\r\n" if "\r\n" in u else "\n"
    rows = []
    for _, d in VARS:
        rows += ["\t\t\t\t<hkobject>", '\t\t\t\t\t<hkparam name="value">%d</hkparam>' % word(d), "\t\t\t\t</hkobject>"]
    u, n_values = insert(u, "wordVariableValues", rows, nl2)
    gd = by_class(folder, "hkbBehaviorGraphData")
    w = rd(gd); nl3 = "\r\n" if "\r\n" in w else "\n"
    rows = []
    for _ in VARS:
        rows += ["\t\t\t\t<hkobject>", '\t\t\t\t\t<hkparam name="role">', "\t\t\t\t\t\t<hkobject>",
                 '\t\t\t\t\t\t\t<hkparam name="role">ROLE_DEFAULT</hkparam>', '\t\t\t\t\t\t\t<hkparam name="flags">0</hkparam>',
                 "\t\t\t\t\t\t</hkobject>", "\t\t\t\t\t</hkparam>", '\t\t\t\t\t<hkparam name="type">VARIABLE_TYPE_REAL</hkparam>',
                 "\t\t\t\t</hkobject>"]
    w, n_infos = insert(w, "variableInfos", rows, nl3)
    # the three appended blocks must line up, or the new names would take another variable's value or type
    if not (n_names == n_values == n_infos):
        raise RuntimeError("%s: appended blocks differ (names %d, values %d, infos %d)" % (graph, n_names, n_values, n_infos))

    nodes = {int(re.search(r"#sdge\$(\d+)", os.path.basename(p)).group(1)): p for p in files(folder)
             if os.path.basename(p).startswith("#sdge$")}
    next_id = max(nodes) + 1
    bound = []
    for i in sorted(nodes):
        p = nodes[i]
        x = rd(p)
        if 'class="hkbClipGenerator"' not in x.split("\n", 1)[0]:
            continue
        nlx = "\r\n" if "\r\n" in x else "\n"
        if '<hkparam name="variableBindingSet">null</hkparam>' not in x:
            raise RuntimeError("%s: clip %s already has a binding set" % (graph, os.path.basename(p)))
        speed = re.search(r'<hkparam name="playbackSpeed">([^<]+)</hkparam>', x).group(1)
        var = {"1.000000": "SDG_DodgeSpeed", "0.900000": "SDG_DodgeSpeedFwdStep"}.get(speed)
        if not var:
            raise RuntimeError("%s: clip %s plays at %s, no variable for it" % (graph, os.path.basename(p), speed))
        new = "#sdge$%d" % next_id
        next_id += 1
        body = nlx.join([
            '\t\t<hkobject name="%s" class="hkbVariableBindingSet" signature="0x338ad4ff">' % new,
            '\t\t\t<hkparam name="bindings" numelements="1">',
            "\t\t\t\t<hkobject>",
            '\t\t\t\t\t<hkparam name="memberPath">playbackSpeed</hkparam>',
            '\t\t\t\t\t<hkparam name="variableIndex">$variableID[%s]$</hkparam>' % var,
            '\t\t\t\t\t<hkparam name="bitIndex">-1</hkparam>',
            '\t\t\t\t\t<hkparam name="bindingType">BINDING_TYPE_VARIABLE</hkparam>',
            "\t\t\t\t</hkobject>",
            "\t\t\t</hkparam>",
            '\t\t\t<hkparam name="indexOfBindingToEnable">-1</hkparam>',
            "\t\t</hkobject>"]) + nlx
        wr(os.path.join(folder, new + ".txt"), body)
        wr(p, x.replace('<hkparam name="variableBindingSet">null</hkparam>',
                        '<hkparam name="variableBindingSet">%s</hkparam>' % new, 1))
        bound.append((os.path.basename(p)[:-4], re.search(r'name="name">([^<]*)<', x).group(1), var))
    wr(sd, t); wr(vs, u); wr(gd, w)
    log.append("%s: 2 variables after %d sdge ones; %d clips bound (%d to SDG_DodgeSpeedFwdStep: %s)" % (
        graph, n_names, len(bound), sum(1 for b in bound if b[2].endswith("FwdStep")),
        ", ".join(b[1] for b in bound if b[2].endswith("FwdStep")) or "-"))


def main():
    log = []
    for g in GRAPHS:
        patch(g, log)
    print("\n".join(log))


if __name__ == "__main__":
    main()
