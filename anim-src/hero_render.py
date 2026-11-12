# hero_render.py - the Nexus identity banner picture for Simple Dodge (2026-11-11, "go ahead and start building the page
# for the simple dodge mod"). One dodge, vanilla steel armour, filmed from a FIXED camera (not riding the root) so the
# step travels across the frame; a few frames are rendered at 1920x1080 plus one empty-floor plate, and hero_composite.py
# ghosts the earlier frames behind the last one.
# Run: blender --background --factory-startup --python hero_render.py -- <Design> <frame> [<frame> ...]
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_stepdodge as B
import showcase_render as S
from mathutils import Vector
from math import radians

args = sys.argv[sys.argv.index("--") + 1:]
D = B.DESIGNS[args[0]]; frames = [int(a) for a in args[1:]]
bpy.ops.wm.open_mainfile(filepath=os.path.join(B.OUT, f"{D.file}.blend"))
arma = bpy.data.objects["StepDodge_Skeleton"]; mr = arma.parent
S.dress(arma); S.stage(D, mr)
sc = bpy.context.scene; cam = sc.camera
T = D.root(D.nf - 1)
mid = Vector((T.x / 2, T.y / 2, 68))
cam.parent = None; cam.data.lens = 40; cam.data.clip_start = 1; cam.data.clip_end = 5000
cam.location = mid + Vector((120, 420, 70))
cam.rotation_euler = (mid - cam.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
out = os.path.join(B.OUT, "_hero", D.name); os.makedirs(out, exist_ok=True)
for f in frames:
    sc.frame_set(f); sc.render.filepath = os.path.join(out, f"{f:03d}.png"); bpy.ops.render.render(write_still=True)
    S.blank_check(sc.render.filepath)
for o in bpy.data.objects:                     # the empty plate: same light and floor, no character
    if o.type == 'MESH' and o.parent == arma: o.hide_render = True
sc.render.filepath = os.path.join(out, "plate.png"); bpy.ops.render.render(write_still=True)
B.say("hero", D.name, frames, "->", out)
