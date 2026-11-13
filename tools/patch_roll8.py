"""Eight directional rolls (1.2.0, the owner, 2026-11-13: "go with the multiple roll dodge animations route, but I want them
to all be the forward dodge animation, just in a different direction").

Before: every roll was the forward roll with the body turned to the stick (item 9) - under True Directional Movement's
target lock the player is kept facing the target, so every roll went toward it. Now each of the eight directions has its
own roll clip (anim-src/build_stepdodge.py, rolls\\Roll<Dir>.hkx: the forward roll with the body turned to the travel
direction and back) and long roll (LongRoll<Dir>.hkx), and the DLL sends the direction's own event.

Per third-person graph with the dodge selectors (1hm_behavior, magicbehavior; mt_behavior is derived by
patch_sheathed.py):
  * the four cardinal roll clip generators (selector slots 0/1) are renamed TKDodgeRoll<Dir> and play
    Animations\\TKDodge\\Roll<Dir>.hkx - their own names, so their motion data is no longer the step's;
  * each diagonal state's selector gets its own roll and long-roll clip generators (slots 0/1 and 4/5; they borrowed the
    forward / back ones), cloned from the forward ones;
  * chain events SDGChainRoll<Dir> for the seven non-forward directions (SDGChainRoll stays forward), each a local
    wildcard of the dodge machine to that direction's state, the same flags and effect as SDGChainRoll's.
and in animationdatasinglefile DefaultMale~1 / DefaultFemale~1: TKDodgeRoll<Dir> (sdge$12..19) and the diagonal
TKDodgeLongRoll<Dir> (sdge$20..23) entries, with the long rolls sdge$8..11 rewritten: the forward roll's motion (sdge$0)
and the long roll's (x1.5) turned to each direction, duration 0.866667. Character files list the 16 clips.
Idempotent: a graph that already has TKDodgeRollLeft is left alone. Valid enum values only (the existing ones are copied).
Usage: python patch_roll8.py
"""
import math, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SDGE = os.path.join(os.path.dirname(HERE), "dist", "Nemesis_Engine", "mod", "sdge")
DIRS = {"Forward": (0.0, 1.0), "Back": (0.0, -1.0), "Left": (-1.0, 0.0), "Right": (1.0, 0.0),
        "ForwardLeft": (-0.7071, 0.7071), "ForwardRight": (0.7071, 0.7071),
        "BackLeft": (-0.7071, -0.7071), "BackRight": (0.7071, -0.7071)}
CARD = ("Forward", "Back", "Left", "Right")
DIAG = ("ForwardLeft", "ForwardRight", "BackLeft", "BackRight")
ROLL_ID = {d: "sdge$%d" % (12 + i) for i, d in enumerate(DIRS)}
LONG_ID = {"Forward": "sdge$8", "Back": "sdge$9", "Left": "sdge$10", "Right": "sdge$11",
           "ForwardLeft": "sdge$20", "ForwardRight": "sdge$21", "BackLeft": "sdge$22", "BackRight": "sdge$23"}
OPEN, CLOSE = "<!-- MOD_CODE ~sdge~ OPEN -->", "<!-- CLOSE -->"
OBJ = re.compile(r'(\t\t<hkobject name="([^"]+)" class="(\w+)".*?\n\t\t</hkobject>)', re.S)


def rd(p): return open(p, "rb").read().decode("utf-8")
def wr(p, t): open(p, "wb").write(t.encode("utf-8"))
def name_of(body): m = re.search(r'name="name">([^<]*)<', body); return m.group(1) if m else ""


def append_to_block(text, list_param, rows, nl):
    for m in re.finditer(re.escape(OPEN), text):
        lists = re.findall(r'<hkparam name="(\w+)" numelements="\d+">', text[:m.start()])
        if lists and lists[-1] == list_param:
            c = text.find(CLOSE, m.end())
            return text[:c] + nl.join(rows) + nl + text[c:]
    raise RuntimeError("no sdge block in %s" % list_param)


def load(folder):
    nodes = {}
    for f in os.listdir(folder):
        if not f.endswith(".txt"): continue
        p = os.path.join(folder, f); t = rd(p)
        for whole, nm, cls in OBJ.findall(t):
            nodes[nm] = dict(path=p, cls=cls, body=whole)
    return nodes


def patch_graph(graph, log):
    folder = os.path.join(SDGE, graph)
    N = load(folder)
    if any(n["cls"] == "hkbClipGenerator" and name_of(n["body"]) == "TKDodgeRollLeft" for n in N.values()):
        log.append("%s: already has the eight rolls" % graph); return
    # the dodge machine: the sdge state machine whose wildcard array carries SDGChainRoll
    sm = [k for k, n in N.items() if n["cls"] == "hkbStateMachine" and k.startswith("#sdge$")
          and "SDGChainRoll" in N.get(re.search(r'wildcardTransitions">([^<]*)<', n["body"]).group(1), {}).get("body", "")]
    assert len(sm) == 1, (graph, sm)
    smb = N[sm[0]]["body"]
    wild = re.search(r'wildcardTransitions">([^<]*)<', smb).group(1)
    states = re.search(r'name="states" numelements="\d+">\s*([^<]*)<', smb).group(1).split()
    # direction of each state: its modifier generator -> selector -> slot 2 (the step clip, TKDodge<Dir>)
    sel_of, sid_of = {}, {}
    for s in states:
        b = N[s]["body"]; g = re.search(r'name="generator">([^<]*)<', b).group(1)
        sel = re.search(r'name="generator">([^<]*)<', N[g]["body"]).group(1)
        gens = re.search(r'name="generators" numelements="\d+">\s*([^<]*)<', N[sel]["body"]).group(1).split()
        d = name_of(N[gens[2]]["body"])[len("TKDodge"):]
        assert d in DIRS, (graph, s, d)
        sel_of[d] = sel; sid_of[d] = int(re.search(r'name="stateId">(\d+)<', b).group(1))
    gens_of = {d: re.search(r'name="generators" numelements="\d+">\s*([^<]*)<', N[sel_of[d]]["body"]).group(1).split()
               for d in DIRS}
    nextid = [max(int(k[6:]) for k in N if k.startswith("#sdge$")) + 1]

    def set_node(key, newbody):
        n = N[key]; t = rd(n["path"]); assert n["body"] in t
        wr(n["path"], t.replace(n["body"], newbody, 1)); n["body"] = newbody

    def clip(body, name, anim):
        body = re.sub(r'name="name">[^<]*<', 'name="name">%s<' % name, body, count=1)
        return re.sub(r'name="animationName">[^<]*<', lambda m: 'name="animationName">Animations\\TKDodge\\%s.hkx<' % anim, body, count=1)

    def new_clip(template, name, anim):
        key = "#sdge$%d" % nextid[0]; nextid[0] += 1
        body = re.sub(r'<hkobject name="[^"]+"', '<hkobject name="%s"' % key, N[template]["body"], count=1)
        body = clip(body, name, anim)
        nl = "\r\n" if "\r\n" in rd(N[template]["path"]) else "\n"
        p = os.path.join(folder, key + ".txt"); wr(p, body.replace("\r\n", "\n").replace("\n", nl) + nl)
        N[key] = dict(path=p, cls="hkbClipGenerator", body=body)
        return key

    def set_slots(d, idx, key):
        n = N[sel_of[d]]
        old = re.search(r'(name="generators" numelements="\d+">\s*)([^<]*)(<)', n["body"])
        toks = old.group(2).split(); ws = re.match(r"\s*", old.group(2)).group(0); tail = old.group(2)[len(old.group(2).rstrip()):]
        for i in idx: toks[i] = key
        nb = n["body"][:old.start(2)] + ws + " ".join(toks) + tail + n["body"][old.end(2):]
        set_node(sel_of[d], nb)

    # cardinal rolls: rename in place (one node per direction)
    roll_node = {}
    for d in CARD:
        k = gens_of[d][0]
        set_node(k, clip(N[k]["body"], "TKDodgeRoll" + d, "Roll" + d)); roll_node[d] = k
    long_node = {d: gens_of[d][4] for d in CARD}
    for d in DIAG:
        r = new_clip(roll_node["Forward"], "TKDodgeRoll" + d, "Roll" + d)
        l = new_clip(long_node["Forward"], "TKDodgeLongRoll" + d, "LongRoll" + d)
        set_slots(d, (0, 1), r); set_slots(d, (4, 5), l)
    # chain events, one per non-forward direction
    sd = [n["path"] for n in N.values() if n["cls"] == "hkbBehaviorGraphStringData"][0]
    gd = [n["path"] for n in N.values() if n["cls"] == "hkbBehaviorGraphData"][0]
    evs = ["SDGChainRoll" + d for d in DIRS if d != "Forward"]
    t = rd(sd); nl = "\r\n" if "\r\n" in t else "\n"
    wr(sd, append_to_block(t, "eventNames", ["\t\t\t\t<hkcstring>%s</hkcstring>" % e for e in evs], nl))
    t = rd(gd); nl = "\r\n" if "\r\n" in t else "\n"
    rows = []
    for e in evs:
        rows += ["\t\t\t\t<hkobject>", '\t\t\t\t\t<hkparam name="flags">0</hkparam>', "\t\t\t\t</hkobject>"]
    wr(gd, append_to_block(t, "eventInfos", rows, nl))
    wb = N[wild]["body"]
    row = re.search(r'(\t\t\t\t<hkobject>\s*<hkparam name="triggerInterval">.*?\n\t\t\t\t</hkobject>)', wb, re.S).group(1)
    assert "$eventID[SDGChainRoll]$" in row
    new_rows = [row.replace("$eventID[SDGChainRoll]$", "$eventID[SDGChainRoll%s]$" % d)
                   .replace('name="toStateId">%d<' % sid_of["Forward"], 'name="toStateId">%d<' % sid_of[d])
                for d in DIRS if d != "Forward"]
    cnt = int(re.search(r'name="transitions" numelements="(\d+)"', wb).group(1))
    nwb = re.sub(r'name="transitions" numelements="\d+"', 'name="transitions" numelements="%d"' % (cnt + len(new_rows)), wb, count=1)
    end = nwb.rindex("\t\t\t</hkparam>")
    nl = "\r\n" if "\r\n" in nwb else "\n"
    set_node(wild, nwb[:end] + nl.join(new_rows) + nl + nwb[end:])
    log.append("%s: cardinal rolls renamed %s; diagonal roll + long roll clips added; %d chain events -> states %s" % (
        graph, roll_node, len(evs), sid_of))


def motion_lines(entry, ux, uy, dur):
    src = rd(os.path.join(SDGE, "animationdatasinglefile", "DefaultMale~1", entry + ".txt")).replace("\r\n", "\n").split("\n")
    n = int(src[2]); out = []
    for k in range(3, 3 + n):
        t, x, y, z = src[k].split(" ")
        y = float(y)
        out.append("%s %s %s 0" % (t, ("%.1f" % (y * ux)) if abs(y * ux) > 1e-3 else "0", ("%.1f" % (y * uy)) if abs(y * uy) > 1e-3 else "0"))
    return out


def patch_animdata(log):
    for proj in ("DefaultMale~1", "DefaultFemale~1"):
        folder = os.path.join(SDGE, "animationdatasinglefile", proj)
        nl = "\r\n" if "\r\n" in rd(os.path.join(folder, "sdge$0.txt")) else "\n"
        for d, (ux, uy) in DIRS.items():
            for kind, mid, src in (("TKDodgeRoll", ROLL_ID[d], "sdge$0"), ("TKDodgeLongRoll", LONG_ID[d], "sdge$8")):
                keys = motion_lines(src, ux, uy, 0.866667)
                lines = [mid, "0.866667", str(len(keys))] + keys + ["1", "0.866667 0 0 0 1", ""]
                wr(os.path.join(folder, mid + ".txt"), nl.join(lines))
                cf = os.path.join(folder, "%s%s~%s.txt" % (kind, d, mid))
                for f in os.listdir(folder):     # a long roll's clip entry keeps its file; others are new
                    if f.endswith("~%s.txt" % mid) and f != os.path.basename(cf):
                        os.remove(os.path.join(folder, f))
                wr(cf, nl.join(["%s%s" % (kind, d), mid, "1", "0", "0", "0", ""]))
    log.append("animdata: 8 rolls (sdge$12..19) and 8 long rolls (sdge$8..11, 20..23), DefaultMale~1 + DefaultFemale~1")


def patch_characters(log):
    for ch in ("defaultmale", "defaultfemale"):
        p = os.path.join(SDGE, ch, "#0029.txt"); t = rd(p); nl = "\r\n" if "\r\n" in t else "\n"
        anchor = "\t\t\t\t<hkcstring>Animations\\TKDodge\\LongRollRight.hkx</hkcstring>" + nl
        assert anchor in t, p
        add = "".join("\t\t\t\t<hkcstring>Animations\\TKDodge\\%s%s.hkx</hkcstring>%s" % (k, d, nl)
                      for k in ("Roll", "LongRoll") for d in DIRS
                      if "TKDodge\\%s%s.hkx<" % (k, d) not in t)
        if add:
            wr(p, t.replace(anchor, anchor + add, 1))
    log.append("character files list the roll clips")


def main():
    log = []
    for g in ("1hm_behavior", "magicbehavior"):
        patch_graph(g, log)
    patch_animdata(log)
    patch_characters(log)
    print("\n".join(log))


if __name__ == "__main__":
    main()
