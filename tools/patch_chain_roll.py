"""Step-to-roll chain - the behaviour side (1.2.0, 2026-11-12; the owner: "lets add an option to chain step dodges into
rol dodges").

In every graph the drawn-weapon patch covers (1hm_behavior, magicbehavior and their first-person graphs; the sheathed
mt_behavior graphs are generated from 1hm by anim-src/patch_sheathed.py, so run that afterwards) this adds:
  * the event SDGChainRoll (eventNames + eventInfos, in the patch's own MOD_CODE blocks);
  * on the dodge's nested state machine (SimpleDodge_Behavior, the one holding the direction states), a local
    wildcard transition on SDGChainRoll to that graph's FORWARD dodge state, allowed from any state including the
    forward state itself (FLAG_ALLOW_SELF_TRANSITION_BY_TRANSITION_FROM_ANY_STATE, and the machine's self-transition
    mode set to blend), using the same blend effect the root's forward dodge transition uses.
The DLL sends SDGChainRoll only inside the chain window of a step dodge, after setting iStep to the roll (so the
forward state's selector picks the roll) and turning the player to the stick direction - every roll is the forward
roll (item 9). Once per chain is the DLL's rule; the graph would accept the event again.
Idempotent: a graph that already has SDGChainRoll is left alone.
Usage: python patch_chain_roll.py [<Nemesis_Engine\\mod\\sdge>]
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SDGE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "dist", "Nemesis_Engine", "mod", "sdge")
EVENT = "SDGChainRoll"
GRAPHS = ["1hm_behavior", "magicbehavior", "_1stperson/1hm_behavior", "_1stperson/magicbehavior"]
OPEN, CLOSE = "<!-- MOD_CODE ~sdge~ OPEN -->", "<!-- CLOSE -->"


def rd(p):
    return open(p, "rb").read().decode("utf-8")


def wr(p, t):
    open(p, "wb").write(t.encode("utf-8"))


def files(folder):
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".txt")]


def by_class(folder, cls):
    out = [p for p in files(folder) if 'class="%s"' % cls in rd(p).split("\n", 1)[0]]
    return out


def append_to_block(text, list_param, rows, nl):
    """Insert rows before the CLOSE of the sdge MOD_CODE block that sits in <list_param>."""
    for m in re.finditer(re.escape(OPEN), text):
        lists = re.findall(r'<hkparam name="(\w+)" numelements="\d+">', text[:m.start()])
        if lists and lists[-1] == list_param:
            c = text.find(CLOSE, m.end())
            return text[:c] + nl.join(rows) + nl + text[c:]
    raise RuntimeError("no sdge block in %s" % list_param)


def row(nl, effect, to_state):
    L = ["\t\t\t\t<hkobject>"]
    for iv in ("triggerInterval", "initiateInterval"):
        L += ['\t\t\t\t\t<hkparam name="%s">' % iv, "\t\t\t\t\t\t<hkobject>",
              '\t\t\t\t\t\t\t<hkparam name="enterEventId">-1</hkparam>', '\t\t\t\t\t\t\t<hkparam name="exitEventId">-1</hkparam>',
              '\t\t\t\t\t\t\t<hkparam name="enterTime">0.000000</hkparam>', '\t\t\t\t\t\t\t<hkparam name="exitTime">0.000000</hkparam>',
              "\t\t\t\t\t\t</hkobject>", "\t\t\t\t\t</hkparam>"]
    L += ['\t\t\t\t\t<hkparam name="transition">%s</hkparam>' % effect,
          '\t\t\t\t\t<hkparam name="condition">null</hkparam>',
          '\t\t\t\t\t<hkparam name="eventId">$eventID[%s]$</hkparam>' % EVENT,
          '\t\t\t\t\t<hkparam name="toStateId">%d</hkparam>' % to_state,
          '\t\t\t\t\t<hkparam name="fromNestedStateId">0</hkparam>',
          '\t\t\t\t\t<hkparam name="toNestedStateId">0</hkparam>',
          '\t\t\t\t\t<hkparam name="priority">0</hkparam>',
          '\t\t\t\t\t<hkparam name="flags">FLAG_ALLOW_SELF_TRANSITION_BY_TRANSITION_FROM_ANY_STATE|FLAG_IS_LOCAL_WILDCARD|FLAG_DISABLE_CONDITION</hkparam>',
          "\t\t\t\t</hkobject>"]
    return nl.join(L)


def patch(graph, log):
    folder = os.path.join(SDGE, *graph.split("/"))
    sd = by_class(folder, "hkbBehaviorGraphStringData")[0]
    t = rd(sd)
    if "<hkcstring>%s</hkcstring>" % EVENT in t:
        log.append("%s: already has %s" % (graph, EVENT)); return
    nl = "\r\n" if "\r\n" in t else "\n"
    wr(sd, append_to_block(t, "eventNames", ["\t\t\t\t<hkcstring>%s</hkcstring>" % EVENT], nl))
    gd = by_class(folder, "hkbBehaviorGraphData")[0]
    t = rd(gd); nl2 = "\r\n" if "\r\n" in t else "\n"
    wr(gd, append_to_block(t, "eventInfos", ["\t\t\t\t<hkobject>", '\t\t\t\t\t<hkparam name="flags">0</hkparam>', "\t\t\t\t</hkobject>"], nl2))
    # the dodge's forward state: where the root wildcard sends TKDodgeForward, and the effect it uses
    fwd = effect = None
    for p in files(folder):
        x = rd(p)
        m = re.search(r'<hkparam name="transition">([^<]+)</hkparam>\s*<hkparam name="condition">[^<]*</hkparam>\s*'
                      r'<hkparam name="eventId">\$eventID\[TKDodgeForward\]\$</hkparam>\s*<hkparam name="toStateId">5695600</hkparam>'
                      r'\s*<hkparam name="fromNestedStateId">\d+</hkparam>\s*<hkparam name="toNestedStateId">(\d+)</hkparam>', x)
        if m:
            effect, fwd = m.group(1), int(m.group(2)); break
    if fwd is None:
        raise RuntimeError("%s: no root transition for TKDodgeForward" % graph)
    # the nested machine: the sdge hkbStateMachine whose states include that stateId
    nodes = {int(re.search(r"#sdge\$(\d+)", os.path.basename(p)).group(1)): p for p in files(folder)
             if os.path.basename(p).startswith("#sdge$")}
    sm = [p for p in nodes.values() if 'class="hkbStateMachine"' in rd(p).split("\n", 1)[0]]
    assert len(sm) == 1, (graph, sm)
    sm = sm[0]; s = rd(sm); nl3 = "\r\n" if "\r\n" in s else "\n"
    assert '<hkparam name="wildcardTransitions">null</hkparam>' in s, graph
    new_id = max(nodes) + 1
    new = "#sdge$%d" % new_id
    s = s.replace('<hkparam name="wildcardTransitions">null</hkparam>', '<hkparam name="wildcardTransitions">%s</hkparam>' % new)
    s = s.replace("SELF_TRANSITION_MODE_NO_TRANSITION", "SELF_TRANSITION_MODE_BLEND")
    wr(sm, s)
    body = nl3.join(['\t\t<hkobject name="%s" class="hkbStateMachineTransitionInfoArray" signature="0xe397b11e">' % new,
                     '\t\t\t<hkparam name="transitions" numelements="1">', row(nl3, effect, fwd), "\t\t\t</hkparam>",
                     "\t\t</hkobject>"]) + nl3
    wr(os.path.join(folder, new + ".txt"), body)
    log.append("%s: %s added; %s (%s) gets wildcard %s -> forward state %d via %s" % (
        graph, EVENT, os.path.basename(sm)[:-4], re.search(r'name="name">([^<]*)', s).group(1), new, fwd, effect))


def main():
    log = []
    for g in GRAPHS:
        patch(g, log)
    print("\n".join(log))


if __name__ == "__main__":
    main()
