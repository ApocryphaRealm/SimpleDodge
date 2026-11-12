"""Sheathed dodge - the Simple Dodge behaviour patch for the weapons-away graph, mt_behavior (2026-11-12).

Why: with the weapon sheathed the character runs 0_master's MT_Behavior_State, whose graph is MT_Behavior.hkx
(0_master: MT_Behavior_State -> MT_LeftHandOverride -> MT_BehaviorBFR "Behaviors\\MT_Behavior.hkx"). The patch only
covered 1hm_behavior (Weap_Readied_State) and magicbehavior (Magic_Behavior_State), so a dodge event sent while
sheathed found no transition and nothing played. The Ultimate Dodge Mod patches mt_behavior the same way
(MT_RootBehavior, #5195) - precedent that the root state machine of that graph is the place for it.

What it writes, per graph (third person and first person), generated from the drawn-weapon patch so the two stay
the same set of dodges (step dodges, rolls, long rolls, diagonals):

  * every #sdge$N node of <src>\\1hm_behavior, copied; literal ids of VANILLA events and variables (FootLeft,
    EndAnimatedCamera, bAllowRotation, bHeadTrackSpine ...) are renumbered by NAME into the target graph, and the
    dodge state's exit transitions go to the target's locomotion state (stateId 0, MT_State) - 1hm sent a blocking
    player to BlockState (1) with a condition on iWantBlock, which mt_behavior does not have;
  * the vanilla data nodes of the target (string data, initial values, graph data) with the dodge events and
    variables appended - a name the target already has (bHeadTracking) is not added twice, and its value and info
    rows are dropped with it so the three lists stay aligned;
  * the target's root state machine with the dodge state appended, and its wildcard transitions with the eight
    dodge transitions.

The target's vanilla nodes come from Nemesis's own vanilla behaviours (Nemesis_Engine\\cached_behaviors), converted
with its hkxcmd.exe, and are laid out the way Nemesis writes them (checked: the converter reproduces The Ultimate
Dodge Mod's de-patched mt_behavior #0083/#0084/#0085/#5194/#5195 and our own 1hm #0085-#0088/#4876 exactly).

The mt_behavior patch is DERIVED: after any change to the 1hm_behavior patch (patch_longroll.py, a new clip, a new
direction), run this again so the sheathed dodges stay the same set.

Usage: python patch_sheathed.py <Nemesis_Engine folder> [<path to Nemesis_Engine\\mod\\sdge>]
       (default patch folder: the repo's dist copy). Rewrites <sdge>\\mt_behavior and <sdge>\\_1stperson\\mt_behavior.
"""
import os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(os.path.dirname(HERE), "dist", "Nemesis_Engine", "mod", "sdge")
OPEN, CLOSE = "<!-- MOD_CODE ~sdge~ OPEN -->", "<!-- CLOSE -->"
# 1hm sends the dodge's end to BlockState when the player holds block; mt has no block and no iWantBlock
EXPR_REWRITE = {
    "(iWantBlock == 1) &amp;&amp; (iLeftHandType != 7) &amp;&amp; (iLeftHandType != 12)": "(i1stPerson == 1)",
    "( iWantBlock == 0 ) &amp;&amp; ( i1stPerson == 0 )": "(i1stPerson == 0)",
}
LOCOMOTION_STATE = "0"  # MT_State in both mt_behavior graphs


def rd(p):
    return open(p, "rb").read().decode("utf-8")


def wr(p, t):
    open(p, "wb").write(t.encode("utf-8"))


# ---- vanilla graphs ---------------------------------------------------------------------------------------------
def convert(nemesis, rel, out):
    hkx = os.path.join(nemesis, "cached_behaviors", rel)
    exe = os.path.join(nemesis, "hkxcmd.exe")
    for p in (hkx, exe):
        if not os.path.isfile(p):
            raise SystemExit("missing %s" % p)
    subprocess.run([exe, "convert", "-v:xml", os.path.abspath(hkx), out], cwd=nemesis, check=True,
                   stdout=subprocess.DEVNULL)
    return open(out, encoding="ascii", errors="replace").read().replace("\r\n", "\n")


def obj(t, nid):
    s = t.find('\t\t<hkobject name="%s"' % nid)
    if s < 0:
        raise RuntimeError("no node %s" % nid)
    return t[s:t.find("\n\t\t</hkobject>", s) + len("\n\t\t</hkobject>")]


def nemesis_layout(block):
    """hkxcmd XML -> Nemesis text: no SERIALIZE_IGNORED comments, one node ref / one float per line."""
    out = []
    for ln in block.split("\n"):
        if re.fullmatch(r"\s*<!-- .* SERIALIZE_IGNORED -->", ln):
            continue
        q = re.fullmatch(r"(\t+)\(([-\d.e]+) ([-\d.e]+) ([-\d.e]+) ([-\d.e]+)\)", ln)
        if q:
            out += [q.group(1) + q.group(k) for k in range(2, 6)]
            continue
        m = re.fullmatch(r"(\t+)((?:#\d+ ?)+)", ln)
        if m:
            out += [m.group(1) + r for r in m.group(2).split()]
            continue
        out.append(ln)
    return "\n".join(out)


def graph(t):
    g = re.search(r'<hkobject name="(#\d+)" class="hkbBehaviorGraph"', t).group(1)
    gb = obj(t, g)
    root = re.search(r'name="rootGenerator">(#\d+)<', gb).group(1)
    data = re.search(r'name="data">(#\d+)<', gb).group(1)
    db = obj(t, data)
    rb = obj(t, root)
    sd = obj(t, re.search(r'name="stringData">(#\d+)<', db).group(1))

    def names(param):
        a = sd[sd.find('<hkparam name="%s"' % param):]
        return re.findall(r"<hkcstring>([^<]*)</hkcstring>", a[:a.find("</hkparam>")])
    states = {}
    for s in re.search(r'name="states"[^>]*>(.*?)</hkparam>', rb, re.S).group(1).split():
        sb = obj(t, s)
        states[re.search(r'name="stateId">([^<]*)', sb).group(1)] = re.search(r'name="name">([^<]*)', sb).group(1)
    return dict(root=root, data=data, strings=re.search(r'name="stringData">(#\d+)<', db).group(1),
                values=re.search(r'name="variableInitialValues">(#\d+)<', db).group(1),
                wildcard=re.search(r'name="wildcardTransitions">([^<]*)<', rb).group(1),
                events=names("eventNames"), variables=names("variableNames"), states=states)


# ---- the drawn-weapon patch -------------------------------------------------------------------------------------
def blocks(text):
    """[(param, body)] for each sdge MOD_CODE block: the list param it sits in and its lines."""
    out = []
    for m in re.finditer(re.escape(OPEN) + r"\r?\n(.*?)" + re.escape(CLOSE), text, re.S):
        lists = re.findall(r'<hkparam name="(eventNames|variableNames|wordVariableValues|variableInfos|eventInfos|'
                           r'transitions|states)" numelements="\d+">', text[:m.start()])
        out.append((lists[-1] if lists else None, m.group(1).replace("\r\n", "\n").rstrip("\n")))
    return out


def chunks(body):
    """Split a block of <hkobject>...</hkobject> rows (4-tab indent) into rows."""
    rows, cur = [], []
    for ln in body.split("\n"):
        cur.append(ln)
        if ln == "\t\t\t\t</hkobject>":
            rows.append("\n".join(cur))
            cur = []
    if cur:
        raise RuntimeError("unterminated row in block")
    return rows


def src_node(folder, cls):
    for f in os.listdir(folder):
        if re.fullmatch(r"#\d{4}\.txt", f) and 'class="%s"' % cls in rd(os.path.join(folder, f)).split("\n", 1)[0]:
            return os.path.join(folder, f)
    raise RuntimeError("%s: no %s" % (folder, cls))


def insert_at_list_end(node, param, body):
    lines = node.split("\n")
    for i, ln in enumerate(lines):
        if re.match(r'\t*<hkparam name="%s" numelements="\d+">' % param, ln):
            indent = ln[:len(ln) - len(ln.lstrip("\t"))]
            if ln.endswith("</hkparam>"):
                raise RuntimeError("empty list %s" % param)
            for j in range(i + 1, len(lines)):
                if lines[j] == indent + "</hkparam>":
                    return "\n".join(lines[:j] + [OPEN] + body.split("\n") + [CLOSE] + lines[j:])
    raise RuntimeError("no list %s" % param)


def build(nemesis, sdge, src_rel, dst_rel, tmp, log):
    src_dir = os.path.join(sdge, *src_rel.split("/"))
    dst_dir = os.path.join(sdge, *dst_rel.split("/"))
    first = dst_rel.startswith("_1stperson")
    sub = "_1stperson\\" if first else ""
    sv = convert(nemesis, sub + "1hm_behavior.hkx", os.path.join(tmp, dst_rel.replace("/", "_") + "_src.xml"))
    dv = convert(nemesis, sub + "mt_behavior.hkx", os.path.join(tmp, dst_rel.replace("/", "_") + "_dst.xml"))
    S, D = graph(sv), graph(dv)
    if D["wildcard"] == "null":
        raise RuntimeError("%s root has no wildcard transitions" % dst_rel)

    # -- the src patch's own vanilla-node blocks
    s_strings = rd(src_node(src_dir, "hkbBehaviorGraphStringData"))
    s_values = rd(src_node(src_dir, "hkbVariableValueSet"))
    s_data = rd(src_node(src_dir, "hkbBehaviorGraphData"))
    s_wild = rd(os.path.join(src_dir, "%s.txt" % S["wildcard"]))
    s_root = rd(os.path.join(src_dir, "%s.txt" % S["root"]))
    sb = blocks(s_strings)
    ev_add = re.findall(r"<hkcstring>([^<]*)</hkcstring>", sb[0][1])
    var_add = re.findall(r"<hkcstring>([^<]*)</hkcstring>", sb[1][1])
    val_rows = chunks(blocks(s_values)[0][1])
    db = blocks(s_data)
    info_rows, evinfo_rows = chunks(db[0][1]), chunks(db[1][1])
    assert len(val_rows) == len(var_add) == len(info_rows), (len(val_rows), len(var_add), len(info_rows))
    assert len(evinfo_rows) == len(ev_add), (len(evinfo_rows), len(ev_add))
    keep_ev = [i for i, n in enumerate(ev_add) if n not in D["events"]]
    keep_var = [i for i, n in enumerate(var_add) if n not in D["variables"]]
    for i, n in enumerate(var_add):
        if i not in keep_var:
            log.append("%s: %s is already a vanilla variable - not added again" % (dst_rel, n))
    for i, n in enumerate(ev_add):
        if i not in keep_ev:
            log.append("%s: %s is already a vanilla event - not added again" % (dst_rel, n))

    if os.path.isdir(dst_dir):
        shutil.rmtree(dst_dir)
    os.makedirs(dst_dir)

    def put(nid, text):
        wr(os.path.join(dst_dir, "%s.txt" % nid), text.replace("\n", "\r\n") + "\r\n")

    # -- target vanilla nodes with our rows appended
    n = nemesis_layout(obj(dv, D["strings"]))
    n = insert_at_list_end(n, "eventNames", "\n".join("\t\t\t\t<hkcstring>%s</hkcstring>" % ev_add[i] for i in keep_ev))
    n = insert_at_list_end(n, "variableNames", "\n".join("\t\t\t\t<hkcstring>%s</hkcstring>" % var_add[i] for i in keep_var))
    put(D["strings"], n)
    n = nemesis_layout(obj(dv, D["values"]))
    put(D["values"], insert_at_list_end(n, "wordVariableValues", "\n".join(val_rows[i] for i in keep_var)))
    n = nemesis_layout(obj(dv, D["data"]))
    n = insert_at_list_end(n, "variableInfos", "\n".join(info_rows[i] for i in keep_var))
    n = insert_at_list_end(n, "eventInfos", "\n".join(evinfo_rows[i] for i in keep_ev))
    put(D["data"], n)
    state_ref = blocks(s_root)[0][1].strip()
    put(D["root"], insert_at_list_end(nemesis_layout(obj(dv, D["root"])), "states", "\t\t\t\t" + state_ref))
    put(D["wildcard"], insert_at_list_end(nemesis_layout(obj(dv, D["wildcard"])), "transitions", blocks(s_wild)[0][1]))
    log.append("%s: vanilla %s/%s/%s + root %s (dodge state %s) + wildcard %s; %d events, %d variables added"
               % (dst_rel, D["strings"], D["values"], D["data"], D["root"], state_ref, D["wildcard"], len(keep_ev), len(keep_var)))

    # -- the new nodes
    state_file = rd(os.path.join(src_dir, state_ref + ".txt"))
    exit_arr = re.search(r'name="transitions">(#sdge\$\d+)<', state_file).group(1)
    count = 0
    for f in sorted(os.listdir(src_dir)):
        if not f.startswith("#sdge$"):
            continue
        t = rd(os.path.join(src_dir, f)).replace("\r\n", "\n")

        def ev(m):
            name = S["events"][int(m.group(2))]
            if name not in D["events"]:
                raise RuntimeError("%s: event %s not in %s" % (f, name, dst_rel))
            return "%s%d%s" % (m.group(1), D["events"].index(name), m.group(3))

        def var(m):
            name = S["variables"][int(m.group(2))]
            if name not in D["variables"]:
                raise RuntimeError("%s: variable %s not in %s" % (f, name, dst_rel))
            return "%s%d%s" % (m.group(1), D["variables"].index(name), m.group(3))
        for key in ("id", "eventId", "activateEventId", "deactivateEventId", "enterEventId", "exitEventId"):
            t = re.sub(r'(<hkparam name="%s">)(\d+)(<)' % key, ev, t)
        t = re.sub(r'(<hkparam name="variableIndex">)(\d+)(<)', var, t)
        for old, new in EXPR_REWRITE.items():
            if old in t:
                t = t.replace(old, new)
                log.append("%s: %s expression -> %s" % (dst_rel, f[:-4], new))
        for e in re.findall(r'<hkparam name="expression">([^<]*)<', t):
            for ident in re.findall(r"[A-Za-z_]\w*", e.replace("&amp;", "")):
                if ident not in D["variables"] and ident not in var_add:
                    raise RuntimeError("%s: expression variable %s not in %s" % (f, ident, dst_rel))
        if f[:-4] == exit_arr:
            for sid in re.findall(r'<hkparam name="toStateId">(\d+)<', t):
                log.append("%s: dodge-state exit to %s (%s) -> %s (%s)" % (dst_rel, sid, S["states"].get(sid),
                                                                          LOCOMOTION_STATE, D["states"][LOCOMOTION_STATE]))
            t = re.sub(r'(<hkparam name="toStateId">)\d+(<)', r"\g<1>%s\g<2>" % LOCOMOTION_STATE, t)
        if re.search(r"#\d{4}\b", t):
            raise RuntimeError("%s refers to a vanilla node" % f)
        wr(os.path.join(dst_dir, f), t.replace("\n", "\r\n"))
        count += 1
    log.append("%s: %d nodes copied from %s" % (dst_rel, count, src_rel))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    nemesis = sys.argv[1]
    sdge = sys.argv[2] if len(sys.argv) > 2 else DEFAULT
    log = []
    tmp = tempfile.mkdtemp(prefix="sdge-sheathed-")
    try:
        build(nemesis, sdge, "1hm_behavior", "mt_behavior", tmp, log)
        build(nemesis, sdge, "_1stperson/1hm_behavior", "_1stperson/mt_behavior", tmp, log)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n".join(log))


if __name__ == "__main__":
    main()
