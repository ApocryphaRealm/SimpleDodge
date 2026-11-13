# check_weapon_clearance.py - does a carried weapon pass through the body during a step dodge? (2026-11-12)
# For each set and direction, every frame: the weapon's long axis (the Weapon node's +Y from a to b units, measured
# from the meshes) against the leg bones (thigh->calf->foot) and the trunk (pelvis->Spine2), as segments. Prints the
# smallest gap per set and where it is. A gap under the limb's own radius (legs ~7 units, trunk ~11) means the weapon is
# inside the body. Run: blender --background --factory-startup --python check_weapon_clearance.py -- [Set ...]
import sys, os, runpy
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [os.path.join(HERE, "build_stepdodge.py")]
M = runpy.run_path(sys.argv[0], run_name="clear")
IDX, DES, solve, DIRS = M["IDX"], M["DESIGNS"], M["solve_pose"], M["STEP_DIRS"]
SPAN = {"Halberd": (-30, 128), "Pike": (-30, 136), "QtrStaff": (-38, 95), "Rapier": (-12, 74), "Katana": (-17, 78),
        "Greatsword": (-14, 115), "BattleaxeWarhammer": (-39, 57), "OneHanded": (-6, 80), "Staff": (-45, 95)}
LIMBS = {"legs": 7.0, "trunk": 11.0}

def seg_dist(p1, q1, p2, q2):
    """Closest distance between segments p1q1 and p2q2 (sampled finely - plenty for a check)."""
    best = 1e9
    for i in range(21):
        a = p1.lerp(q1, i / 20)
        d2 = q2 - p2; t = max(0.0, min(1.0, (a - p2).dot(d2) / max(d2.length_squared, 1e-9)))
        best = min(best, (a - (p2 + d2 * t)).length)
    return best

sets = args or [s for s in SPAN if any((d + s) in DES for d in DIRS)]
for s in sets:
    worst = {"legs": (1e9, ""), "trunk": (1e9, "")}
    a, b = SPAN[s]
    for d in DIRS:
        D = DES.get(d + s)
        if D is None: continue
        for f in range(D.nf):
            G = solve(D, f)[0]
            W = G[IDX["Weapon"]]; y = W.to_3x3().col[1].normalized(); o = W.translation
            # skip the part of the weapon inside the gripping hand(s): start 10 units past the grip each way
            p, q = o + y * a, o + y * b
            pos = lambda n: G[IDX[n]].translation
            bones = {"legs": [], "trunk": [(pos("NPC Pelvis [Pelv]"), pos("NPC Spine2 [Spn2]"))]}
            for sd in "LR":
                bones["legs"] += [(pos(f"NPC {sd} Thigh [{sd}Thg]"), pos(f"NPC {sd} Calf [{sd}Clf]")),
                                  (pos(f"NPC {sd} Calf [{sd}Clf]"), pos(f"NPC {sd} Foot [{sd}ft ]"))]
            for k, segs in bones.items():
                for s1, s2 in segs:
                    g = seg_dist(p, q, s1, s2)
                    if g < worst[k][0]: worst[k] = (g, "%s f%d" % (d, f))
    flag = [k for k in worst if worst[k][0] < LIMBS[k]]
    print("CLEAR %-20s legs %5.1f (%s)  trunk %5.1f (%s)  %s" % (s, worst["legs"][0], worst["legs"][1], worst["trunk"][0],
          worst["trunk"][1], "INSIDE: " + ",".join(flag) if flag else "ok"))
