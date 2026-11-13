# check_grip_contact.py - are both hands ON a two-handed weapon in every frame? FAILS (exit 1) when not. (2026-11-12,
# the owner: "The hands dont line up on the pike dodge or the qtr staff either".)
# The shaft is the Weapon node's +Y line (every weapon mesh's long axis, measured from the nifs; the mesh's grip origin
# is the node). Each hand has its own grip node, the point and axis the game holds a weapon by in that hand: the right
# hand's is the Weapon node as the hand carries it (the hand's own Weapon-node offset - what a one-handed weapon in that
# hand would use), the left hand's the Shield node (where a left-hand weapon's grip goes). Per set, direction and frame:
# that grip node's distance from the shaft line, and the angle between its +Y and the shaft (0 = aligned, sign ignored).
# Calibrated on the game's own idles: the vanilla right-hand grip measures exactly 0 / 0 this way.
# Limits: 1.0 unit and 15 degrees. Run: blender --background --factory-startup --python check_grip_contact.py -- [Set ...]
import sys, os, math, runpy
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [os.path.join(HERE, "build_stepdodge.py")]
M = runpy.run_path(sys.argv[0], run_name="grip")
IDX, DES, solve, DIRS = M["IDX"], M["DESIGNS"], M["solve_pose"], M["STEP_DIRS"]
DIST_MAX, ANGLE_MAX = 1.0, 15.0
# which hands hold the weapon, per set
HANDS = {"Greatsword": "RL", "BattleaxeWarhammer": "RL", "Katana": "RL", "Halberd": "RL", "Pike": "RL", "QtrStaff": "RL",
         "Staff": "R", "Bow": "L", "Crossbow": "RL"}

def fist(G, s):
    names = [f"NPC {s} Finger{d}{j} [{s}F{d}{j}]" for d in "1234" for j in "01"]
    pts = [G[IDX[n]].translation for n in names]
    c = sum(pts, pts[0] * 0) / len(pts)
    axis = (G[IDX[f"NPC {s} Finger40 [{s}F40]"]].translation - G[IDX[f"NPC {s} Finger10 [{s}F10]"]].translation).normalized()
    return c, axis

def grip_node(D, G, s):
    """World frame of the hand's own grip node: R = Weapon offset carried by the hand, L = Shield."""
    node = "Weapon" if s == "R" else "Shield"
    i = IDX[node]; par = M["PAR"][i]
    GL = D.__dict__.get("_grip_L") or {}
    local = GL.get(i, M["L0"][i])
    return G[par] @ local

def measure(D, f):
    G = solve(D, f)[0]
    W = G[IDX["Weapon"]]; o = W.translation; y = W.to_3x3().col[1].normalized()
    out = {}
    for s in HANDS[D.grip_set]:
        g = grip_node(D, G, s)
        c, ax = g.translation, g.to_3x3().col[1].normalized()
        v = c - o
        dist = (v - y * v.dot(y)).length
        ang = math.degrees(math.acos(min(1.0, abs(ax.dot(y)))))
        out[s] = (dist, ang, v.dot(y))
    return out

# Sets that hold the weapon with a VANILLA idle's arms (GRIPS): the game's own pose is the reference - the left hand
# must sit on the weapon exactly as it does in that idle. The idle relation is rebuilt from its parent-local chain with
# the chest at rest (both arms hang from Spine2), so a drift of our clip from the game's grip shows as a difference.
from mathutils import Matrix
def vanilla_relation(D):
    GL = D.__dict__.get("_grip_L") or {}
    PAR, L0, ch = M["PAR"], M["L0"], IDX["NPC Spine2 [Spn2]"]
    def world(i):
        chain = []
        while i != ch:
            chain.append(i); i = PAR[i]
        m = Matrix.Identity(4)
        for j in reversed(chain):
            m = m @ GL.get(j, L0[j])
        return m
    return world(IDX["Weapon"]).inverted() @ world(IDX["Shield"])

def measure_vanilla(D, f):
    G = solve(D, f)[0]
    rel = G[IDX["Weapon"]].inverted() @ G[IDX["Shield"]]
    ref = vanilla_relation(D)
    dist = (rel.translation - ref.translation).length
    q = rel.to_quaternion().rotation_difference(ref.to_quaternion())
    return dist, math.degrees(q.angle)

if __name__ == "__main__":
    sets = args or list(HANDS)
    bad = 0
    for s in sets:
        worst = {}
        if getattr(DES.get(DIRS[0] + s), "grip_spec", None) is not None:
            wd = wa = 0.0; at = ""
            for d in DIRS:
                D = DES.get(d + s)
                for f in range(D.nf):
                    dist, ang = measure_vanilla(D, f)
                    if dist > wd or ang > wa: wd, wa, at = max(wd, dist), max(wa, ang), "%s f%d" % (d, f)
            ok = wd <= DIST_MAX and wa <= ANGLE_MAX
            bad += 0 if ok else 1
            print("GRIP %-20s both hands as the game's idle: drift %4.2f units, %4.1f deg (%s)  %s" % (
                s, wd, wa, at or "-", "ok" if ok else "FAIL"))
            continue
        for d in DIRS:
            D = DES.get(d + s)
            if D is None: continue
            for f in range(D.nf):
                for h, (dist, ang, along) in measure(D, f).items():
                    w = worst.setdefault(h, [0, "", 0, "", 0])
                    if dist > w[0]: w[0], w[1] = dist, "%s f%d" % (d, f)
                    if ang > w[2]: w[2], w[3] = ang, "%s f%d" % (d, f)
                    w[4] = along
        for h, (dist, wd, ang, wa, along) in sorted(worst.items()):
            ok = dist <= DIST_MAX and ang <= ANGLE_MAX
            bad += 0 if ok else 1
            print("GRIP %-20s %s hand: off-axis %5.1f (%s)  angle %5.1f (%s)  at %5.1f along  %s" % (
                s, h, dist, wd, ang, wa, along, "ok" if ok else "FAIL"))
    print("GRIP RESULT", "FAIL %d" % bad if bad else "PASS")
    sys.exit(1 if bad else 0)
