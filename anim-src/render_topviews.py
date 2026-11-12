# render_topviews.py - extra review angles the owner asked for (2026-11-11: "from on top, looking down, or also from
# behind the character, looking down at an angle"): a top-down view over the whole travel and a high three-quarter
# view from behind that rides the root. Reuses the review scene build_stepdodge.py's render stage saved
# (_preview_<Design>.blend: skinned body, floor grid, Workbench look). Frames go to _frames_top\<Design>\.
# Run: blender --background --factory-startup --python render_topviews.py -- <Design> [...]
import bpy, sys, os
from math import radians
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__))

def cam(sc, name, ortho=None, lens=35):
    cd = bpy.data.cameras.new(name)
    if ortho: cd.type = 'ORTHO'; cd.ortho_scale = ortho
    else: cd.lens = lens
    co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co)
    return co

def aim(co, target):
    co.rotation_euler = (target - co.location).to_track_quat('-Z', 'Y').to_euler()

def run(name):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, f"_preview_{name}.blend"))
    sc = bpy.context.scene
    arma = bpy.data.objects["StepDodge_Skeleton"]; mr = arma.parent
    sc.frame_set(sc.frame_end); end = mr.matrix_world.translation.copy(); sc.frame_set(1)
    mid = end / 2
    span = max(abs(end.x), abs(end.y)) + 160
    top = cam(sc, "CamTop", ortho=span); top.location = (mid.x, mid.y, 900); top.rotation_euler = (0, 0, 0)
    back = cam(sc, "CamBack", lens=30); back.parent = mr
    back.location = Vector((0, -330, 260)); aim(back, Vector((0, 40, 60)))
    out = os.path.join(HERE, "_frames_top", name); os.makedirs(out, exist_ok=True)
    for f in range(sc.frame_start, sc.frame_end + 1):
        sc.frame_set(f)
        for c in (top, back):
            sc.camera = c; sc.render.resolution_x, sc.render.resolution_y = 720, 720
            sc.render.filepath = os.path.join(out, f"{c.name}_{f:03d}.png")
            bpy.ops.render.render(write_still=True)
    print("TOPVIEWS", name, sc.frame_end, "frames")

for n in sys.argv[sys.argv.index("--") + 1:]:
    run(n)
