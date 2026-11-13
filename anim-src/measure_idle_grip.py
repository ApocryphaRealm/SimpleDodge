# measure_idle_grip.py - where an idle holds its weapon, as POLES numbers (2026-11-13). For each idle: the Weapon
# node's position and +Y axis and the roll of its +X about that axis, in the chest's REST frame (what POLES' grip / dir
# / roll mean), and the left hand's Shield node as a spread along the shaft plus its distance from the shaft line.
# Only numbers are read (a direction and a point), to author our own grip from; no pose data is copied into a clip.
# Run: blender --background --factory-startup --python measure_idle_grip.py -- <idle.hkx | vanilla name> [...]
import sys, os, math, runpy
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [os.path.join(HERE, "check_weapon_continuity.py"), "--", "__none__"]
C = runpy.run_path(os.path.join(HERE, "check_weapon_continuity.py"), run_name="measure")
from mathutils import Matrix, Vector
IDX, PAR, L0, CH = C["IDX"], C["PAR"], C["L0"], C["CH"]
G0 = C["M"]["G0"] if "M" in C else None

def chest_local(locs, bone):
    i = IDX[bone]; chain = []
    while i != CH:
        chain.append(i); i = PAR[i]
    m = Matrix.Identity(4)
    for j in reversed(chain):
        m = m @ locs.get(j, L0[j])
    return m

for ref in args:
    locs = C["locals_of"](ref)
    G0ch = C["M"]["G0"][CH]
    W = G0ch @ chest_local(locs, "Weapon"); S = G0ch @ chest_local(locs, "Shield")
    y = W.to_3x3().col[1].normalized(); x = W.to_3x3().col[0].normalized()
    up = Vector((0, 0, 1)); x0 = y.cross(up).normalized()
    roll = math.degrees(math.atan2(x0.cross(x).dot(y), x0.dot(x)))
    sx = S.to_3x3().col[0].normalized(); sy = S.to_3x3().col[1].normalized()
    left_roll = math.degrees(math.atan2(x.cross(sx).dot(y), x.dot(sx)))
    left_axis_angle = math.degrees(math.acos(max(-1, min(1, abs(sy.dot(y))))))
    v = S.translation - W.translation
    along = v.dot(y); off = (v - y * along).length
    print("IDLE %s grip=(%.1f, %.1f, %.1f) dir=(%.3f, %.3f, %.3f) roll=%.1f spread=%.1f left_off_shaft=%.1f left=(%.1f, %.1f, %.1f) left_roll=%.1f left_axis_angle=%.1f" % (
        os.path.basename(ref), *W.translation, *y, roll, along, off, *S.translation, left_roll, left_axis_angle))
