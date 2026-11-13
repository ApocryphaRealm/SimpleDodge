"""First-person diagonals - the behaviour side (1.2.0, 2026-11-13; the owner: "Build the first-person diagonals", after
Nexus user 1m0ws asked for 8-way first-person dodging).

Before: the first-person graphs had the four diagonal events, but their wildcard transitions went into the dodge machine's
FORWARD and BACK states (toNestedStateId 3 / 2 in 1hm, 4 / 3 in magic), so a diagonal press in first person played the
straight forward or back dodge. FirstPerson~1 had only the four straight motions.

This adds, in each first-person graph the drawn-weapon patch covers (_1stperson/1hm_behavior, _1stperson/magicbehavior;
_1stperson/mt_behavior is GENERATED from 1hm by anim-src/patch_sheathed.py - run that afterwards):
  * four states on the dodge's nested state machine (SimpleDodge_Behavior), TKDodgeForwardLeft / ForwardRight /
    BackLeft / BackRight, each with its own clip generator (same name, so FirstPerson~1's clip entry of that name gives
    its motion) playing Animations\\TKDodge\\StepDodge<Dir>.hkx under _1stperson (our own clips, anim-src/
    build_fp_diagonals.py), and its own trigger array;
  * the states, clips and triggers are COPIED from that graph's own forward (forward diagonals) or back (back diagonals)
    state, so every event and variable number in them is already the graph's own (clip triggers hold vanilla foot
    event ids that differ per graph) and the timings fit: forward diagonals are 1.0 s clips that end the dodge 0.4 s
    before their end, as the forward roll does; back diagonals 0.9 s clips that end it 0.3 s before, as the back step;
  * state ids after the machine's highest (1hm 4-7; magic 5-8, since magic's forward state is already 4);
  * the parent's wildcard rows for the four diagonal events (already copies of the forward / back rows, same flags,
    effect and condition) retargeted to the new states (toNestedStateId).
and, in animationdatasinglefile\\FirstPerson~1, a clip entry and a motion entry per diagonal (animdata() below).
The four clip files are listed in the first-person character (_1stperson/firstperson/#0029, written once by hand from
the vanilla string data - see the 2026-11-13 commit).
Idempotent: a graph whose dodge machine already has a TKDodgeForwardLeft state is left alone.
Usage: python patch_fp_diagonals.py [<Nemesis_Engine\\mod\\sdge>]
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDGE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "dist", "Nemesis_Engine", "mod", "sdge")
GRAPHS = ["_1stperson/1hm_behavior", "_1stperson/magicbehavior"]
DIAGONALS = [("ForwardLeft", "Forward"), ("ForwardRight", "Forward"), ("BackLeft", "Back"), ("BackRight", "Back")]


def rd(p):
    return open(p, "rb").read().decode("utf-8")


def wr(p, t):
    open(p, "wb").write(t.encode("utf-8"))


def nodes(folder):
    out = {}
    for f in os.listdir(folder):
        if f.endswith(".txt"):
            t = rd(os.path.join(folder, f))
            m = re.search(r'<hkobject name="([^"]+)" class="(\w+)"', t)
            if m:
                out[m.group(1)] = (m.group(2), t, f)
    return out


def param(t, name):
    return re.search(r'<hkparam name="%s">([^<]*)<' % name, t).group(1)


def setparam(t, name, value):
    t2, n = re.subn(r'(<hkparam name="%s">)[^<]*(<)' % name, lambda m: m.group(1) + value + m.group(2), t, count=1)
    assert n == 1, name
    return t2


def rename(t, old, new):
    return t.replace('<hkobject name="%s"' % old, '<hkobject name="%s"' % new, 1)


def patch(graph):
    folder = os.path.join(SDGE, *graph.split("/"))
    N = nodes(folder)
    machines = [k for k, (c, t, f) in N.items() if c == "hkbStateMachine" and param(t, "name") == "SimpleDodge_Behavior"]
    assert len(machines) == 1, (graph, machines)
    sm = machines[0]
    smt = N[sm][1]
    nl = "\r\n" if "\r\n" in smt else "\n"
    lst = re.search(r'(<hkparam name="states" numelements=")(\d+)(">)(.*?)(</hkparam>)', smt, re.S)
    refs = lst.group(4).split()
    states = {param(N[r][1], "name"): r for r in refs}
    if "TKDodgeForwardLeft" in states:
        return "%s: already has the diagonal states - left alone" % graph
    ids = [int(param(N[r][1], "stateId")) for r in refs]
    nxt = max(int(k.split("$")[1]) for k in N if k.startswith("#sdge$")) + 1
    sid = max(ids) + 1
    log, new_ids = [], {}
    for d, src in DIAGONALS:
        st = N[states["TKDodge" + src]][1]
        gen = param(st, "generator")
        gt = N[gen][1]
        trg = param(gt, "triggers")
        tt = N[trg][1]
        n_trg, n_gen, n_st = ("#sdge$%d" % (nxt + k) for k in range(3))
        nxt += 3
        wr(os.path.join(folder, n_trg + ".txt"), rename(tt, trg, n_trg))
        g = rename(gt, gen, n_gen)
        g = setparam(g, "name", "TKDodge" + d)
        g = setparam(g, "animationName", "Animations\\TKDodge\\StepDodge%s.hkx" % d)
        g = setparam(g, "triggers", n_trg)
        wr(os.path.join(folder, n_gen + ".txt"), g)
        s = rename(st, states["TKDodge" + src], n_st)
        s = setparam(s, "generator", n_gen)
        s = setparam(s, "name", "TKDodge" + d)
        s = setparam(s, "stateId", str(sid))
        wr(os.path.join(folder, n_st + ".txt"), s)
        refs.append(n_st)
        new_ids[d] = sid
        log.append("%s: TKDodge%s state %s (stateId %d) <- %s, clip %s, triggers %s" % (graph, d, n_st, sid, src, n_gen, n_trg))
        sid += 1
    smt = smt[:lst.start()] + lst.group(1) + str(len(refs)) + lst.group(3) + nl + "\t\t\t\t" + " ".join(refs) + nl + \
        "\t\t\t" + lst.group(5) + smt[lst.end():]
    wr(os.path.join(SDGE, *graph.split("/"), N[sm][2]), smt)
    # the parent's wildcard rows for the diagonal events
    done = 0
    for k, (c, t, f) in N.items():
        if c != "hkbStateMachineTransitionInfoArray" or k.startswith("#sdge$"):
            continue
        t2 = t
        for d, sidd in new_ids.items():
            pat = re.compile(r'(<hkparam name="eventId">\$eventID\[TKDodge%s\]\$</hkparam>.*?<hkparam name="toNestedStateId">)'
                             r'(\d+)(<)' % d, re.S)
            t2, n = pat.subn(lambda m: m.group(1) + str(sidd) + m.group(3), t2)
            done += n
        if t2 != t:
            wr(os.path.join(folder, f), t2)
            log.append("%s: %s diagonal wildcard rows -> nested states %s" % (graph, k, sorted(new_ids.values())))
    assert done == 4, (graph, done)
    return "\n".join(log)


def animdata():
    """FirstPerson~1: a clip entry and a motion entry per diagonal. The motion is the third-person diagonal's
    (DefaultMale~1 sdge$4..7, the same in DefaultFemale~1), under this project's own ids sdge$0..3; the clip entry
    is laid out like the first-person cardinals' (TKDodgeStop at the motion's end). Rewritten every run."""
    ad = os.path.join(SDGE, "animationdatasinglefile")
    out = []
    for k, (d, _) in enumerate(DIAGONALS):
        src = "sdge$%d" % (4 + k)
        dst = "sdge$%d" % k
        lines = rd(os.path.join(ad, "DefaultMale~1", src + ".txt")).split("\r\n")
        assert lines[0] == src, (src, lines[0])
        lines[0] = dst
        wr(os.path.join(ad, "FirstPerson~1", dst + ".txt"), "\r\n".join(lines))
        dur = lines[1]
        wr(os.path.join(ad, "FirstPerson~1", "TKDodge%s~%s.txt" % (d, dst)),
           "\r\n".join(["TKDodge" + d, dst, "1", "0", "0", "1", "TKDodgeStop:%s" % dur]) + "\r\n")
        out.append("FirstPerson~1: TKDodge%s -> %s (motion of DefaultMale~1 %s, %s s, end %s)"
                   % (d, dst, src, dur, lines[2 + int(lines[2])]))
    return "\n".join(out)


def main():
    for g in GRAPHS:
        print(patch(g))
    print(animdata())


if __name__ == "__main__":
    main()
