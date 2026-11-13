# check_weapon_continuity.py - does a weapon set's dodge start and end with the weapon pointing the way the idle the
# player stands in points it? FAILS (exit 1) when the weapon's long axis differs by more than 20 degrees at the first
# or the last frame of any direction. (2026-11-13, the owner, playing: "The spear dodge animation swaps the weapon
# direction unlike the vanilla weapons. Make it similar.")
# The weapon axis is the Weapon node's +Y (every weapon mesh's long axis), in the chest's (Spine2) frame. The idle's is
# built from the idle's frame-0 parent-local chain (root to Weapon; bones the idle has no track for at rest), the
# dodge's from solve_pose at that frame.
# Which idle a set must match: a vanilla-type set its own GRIPS idle; a keyword set the idle its weapons actually stand
# in - Animated Armoury's pike idle for its pikes/spears (_work/aa-view, private, never shipped); for a set whose
# weapons have no idle of their own (Heavy Armory, OCF keywords on vanilla animation types) both vanilla two-handed
# idles, since the weapon's own animation type decides which one plays.
# Run: blender --background --factory-startup --python check_weapon_continuity.py -- [Set ...]
import sys, os, math, runpy
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [os.path.join(HERE, "build_stepdodge.py")]
M = runpy.run_path(sys.argv[0], run_name="cont")
from mathutils import Matrix, Quaternion, Vector
IDX, DES, solve, DIRS, PAR, L0, AS = M["IDX"], M["DESIGNS"], M["solve_pose"], M["STEP_DIRS"], M["PAR"], M["L0"], M["AS"]
LIMIT = 20.0
AA = os.path.join(os.path.dirname(HERE), "_work", "aa-view")
REFS = {   # set -> idles its weapons stand in (vanilla name, or an absolute path)
    "Pike": [os.path.join(AA, "pike_idle.hkx")],
    "Halberd": [os.path.join(AA, "pike_idle.hkx")],     # given the pike stance: AA's own halberd idle not read
    "QtrStaff": [os.path.join(AA, "pike_idle.hkx")],    # the same for the quarterstaff
    "Rapier": [os.path.join(AA, "rapier_idle.hkx")],
    "Katana": [os.path.join(AA, "katana_idle.hkx")],
}
_cache = {}
def locals_of(name):
    if name in _cache: return _cache[name]
    p = name if os.path.isabs(name) else os.path.join(M["VANILLA_ANIMS"], *name.split("/")) + ".hkx"
    a = AS.load_skyrim_animation(p)
    binding = list(a.track_to_bone_indices) or list(range(len(a.tracks)))
    out = {}
    for tr, bi in enumerate(binding):
        if bi < 0 or tr >= len(a.tracks): continue
        t_, r_ = a.tracks[tr].translations[0], a.tracks[tr].rotations[0]
        out[bi] = Matrix.Translation(Vector(t_)) @ Quaternion((r_[3], r_[0], r_[1], r_[2])).to_matrix().to_4x4()
    _cache[name] = out
    return out

CH = IDX["NPC Spine2 [Spn2]"]
def axis_world(locs, bone="Weapon"):
    """the weapon axis in the chest (Spine2) frame: the stance below the chest is the dodge's own in every set, so the
    grip is what a set changes - and what the eye reads as the weapon turning when the dodge starts"""
    i = IDX[bone]; chain = []
    while i != CH:
        chain.append(i); i = PAR[i]
    m = Matrix.Identity(4)
    for j in reversed(chain):
        m = m @ locs.get(j, L0[j])
    return m.to_3x3().col[1].normalized()

def angle(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, a.dot(b)))))

if __name__ == "__main__":
    sets = args or [s for s in M["GRIPS"]] + list(M["POLES"])
    bad = 0
    for s in sets:
        D0 = DES.get(DIRS[0] + s)
        if D0 is None: continue
        refs = REFS.get(s) or [D0.grip_spec["R"][0]] if getattr(D0, "grip_spec", None) else REFS.get(s, [])
        if not refs:
            print("CONT %-20s no reference idle - not judged" % s); continue
        for ref in refs:
            ra = axis_world(locals_of(ref))
            worst, at = 0.0, "-"
            for d in DIRS:
                D = DES[d + s]
                for f in (0, D.nf - 1):
                    G = solve(D, f)[0]
                    ax = (G[CH].to_3x3().inverted() @ G[IDX["Weapon"]].to_3x3().col[1]).normalized()
                    ang = angle(ax, ra)
                    if ang > worst: worst, at = ang, "%s f%d" % (d, f)
            ok = worst <= LIMIT
            bad += 0 if ok else 1
            print("CONT %-20s vs %-22s worst %5.1f deg (%s)  %s" % (s, os.path.basename(ref), worst, at, "ok" if ok else "FAIL"))
    print("CONT RESULT", "FAIL %d" % bad if bad else "PASS")
    sys.exit(1 if bad else 0)
