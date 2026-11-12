# measure_steps.py - numbers for the step dodges of a build_stepdodge.py (the 2026-11-12 rework's before/after proof).
# Runs the build script's own pose solver (no .hkx read) and prints, per direction, as JSON:
#   pelvis_z   NPC Pelvis height: stance (frame 0), lowest, at the lead foot's landing
#   lead       the foot that lands first, and its landing frame (first grounded frame after its swing)
#   knee_flex  that leg's knee flexion (0 = straight) at landing, and the deepest through the next 5 frames
#   knee_in    where that knee points, in degrees from the pelvis's forward toward the body's centre line
#              (+ = inward, toward the other leg; - = splayed out), at landing; and its offset (units) from the
#              hip-ankle line toward the centre line
#   lean       the chest's (Spine2, from the pelvis) tilt toward the direction of travel, degrees, relative to the
#              stance at frame 0: the most before landing, and at the last frame (recovered = near 0)
# Run: blender --background --factory-startup --python measure_steps.py -- <build script> <out.json> [Dir ...]
import sys, os, json, math, runpy
args = sys.argv[sys.argv.index("--") + 1:]
script, out = args[0], args[1]
dirs = args[2:] or ["Left", "Right", "Forward", "Back", "ForwardLeft", "ForwardRight", "BackLeft", "BackRight"]
sys.argv = [script]                        # the build script reads no stages when not run as __main__
M = runpy.run_path(script, run_name="sd_measure")
from mathutils import Vector
solve, IDX, DES = M["solve_pose"], M["IDX"], M["DESIGNS"]

def pos(G, n): return G[IDX[n]].translation

res = {}
for d in dirs:
    D = DES[d]
    frames = [solve(D, f) for f in range(D.nf)]
    T = D.root(D.nf - 1); trav = Vector((T.x, T.y, 0)).normalized()
    # landing frame of each foot: first grounded frame after it has been lifted
    land = {}
    for side, pre in (("L", "lf"), ("R", "rf")):
        up, start = False, None
        for f in range(D.nf):
            x, y, lift = D.foot(pre, f)[:3]
            if lift > 0.5 and not up: up, start = True, Vector((x, y, 0))
            elif up and lift <= 0.05:
                if (Vector((x, y, 0)) - start).length > 40.0:     # a travelling step, not a stance-switch shuffle
                    land[side] = f; break
                up = False
    lead = min(land, key=land.get) if land else "L"
    fl = land.get(lead, D.nf - 1)
    def knee(G, side):
        h = pos(G, f"NPC {side} Thigh [{side}Thg]"); k = pos(G, f"NPC {side} Calf [{side}Clf]"); a = pos(G, f"NPC {side} Foot [{side}ft ]")
        flex = math.degrees((k - h).angle(a - k))
        other = pos(G, "NPC %s Thigh [%sThg]" % (("R", "R") if side == "L" else ("L", "L")))
        medial = (other - h); axis = (a - h).normalized()
        medial = (medial - axis * medial.dot(axis)).normalized()
        # pelvis forward: the root's +Y turned by the hips' own yaw - taken from the two thighs: perpendicular to the
        # hip line, horizontal
        hip_line = (other - h); f2 = Vector((0, 0, 1)).cross(hip_line).normalized()
        if f2.y < 0: f2 = -f2
        f2 = (f2 - axis * f2.dot(axis)).normalized()
        o = k - (h + axis * (k - h).dot(axis))
        ang = math.degrees(math.atan2(o.dot(medial), o.dot(f2)))
        return flex, ang, o.dot(medial)
    def lean(G):
        c = G[IDX["NPC Spine2 [Spn2]"]]; p = pos(G, "NPC Pelvis [Pelv]")
        upv = (c.translation - p).normalized()
        return math.degrees(math.atan2(upv.dot(trav), upv.z))
    pz = [pos(G, "NPC Pelvis [Pelv]").z for G, r, ft in frames]
    flex_l, ang_l, off_l = knee(frames[fl][0], lead)
    flex_max = max(knee(frames[f][0], lead)[0] for f in range(fl, min(D.nf, fl + 6)))
    leans = [lean(G) for G, r, ft in frames]
    res[d] = dict(frames=D.nf, lead=lead, landing_frame=fl,
                  pelvis_z=dict(stance=round(pz[0], 1), lowest=round(min(pz), 1), at_landing=round(pz[fl], 1)),
                  knee_flex=dict(at_landing=round(flex_l, 1), deepest_after=round(flex_max, 1)),
                  knee_in=dict(at_landing_deg=round(ang_l, 1), offset_toward_centre=round(off_l, 1)),
                  lean=dict(max_before_landing=round(max(leans[:fl + 1]) - leans[0], 1),
                            last_frame=round(leans[-1] - leans[0], 1), stance_raw=round(leans[0], 1)))
    print(d, json.dumps(res[d]))
json.dump(res, open(out, "w"), indent=1)
