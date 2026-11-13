# render_reference.py - LOOK at another mod's weapon-type animation before posing our own (2026-11-12, the owner:
# "load each weapon type into blender with the character body so you can see the animations play out with the weapon
# in hand"). Loads one .hkx clip onto our armature with PyNifly, attaches the weapon nif(s) to their nodes, and renders
# front and side frames through build_stepdodge.py's own render stage. Nothing here is written into our clips: the
# frames are for looking, and our grips are authored separately (GRIPS in build_stepdodge.py).
# Run: blender --background --factory-startup --python render_reference.py -- <name> <clip.hkx> <node>=<nif> [...]
#      frames land in _frames/<name>/  (make_review_mp4.py turns them into a clip)
import sys, os, runpy
args = sys.argv[sys.argv.index("--") + 1:]
name, clip = args[0], args[1]
meshes = [a.split("=", 1) for a in args[2:]]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [os.path.join(HERE, "build_stepdodge.py")]
M = runpy.run_path(sys.argv[0], run_name="ref")
import bpy
from mathutils import Vector

M["clear_scene"]()
sc = bpy.context.scene
arma = M["import_armature"]()
mr = bpy.data.objects.new("MotionData_Root (preview travel)", None); sc.collection.objects.link(mr)
arma.parent = mr
bpy.context.view_layer.objects.active = arma; arma.select_set(True)
r = bpy.ops.import_scene.pynifly_hkx(filepath=clip)
act = arma.animation_data.action
fs, fe = int(act.frame_range[0]), int(act.frame_range[1])
nf = min(fe - fs + 1, 60)                      # at most 2 s of a looping idle
sc.frame_start, sc.frame_end = 1, nf
os.makedirs(os.path.join(HERE, "_reference"), exist_ok=True)
rel = os.path.join("_reference", name)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, rel + ".blend"))
M["WEAPON_MESHES"][name] = [(node, nif) for node, nif in meshes]

class Ref:
    pass
D = Ref()
D.name, D.file, D.nf, D.weapon_show = name, rel, nf, name
D.root = lambda f: Vector((0, 0, 0))
M["render"](D)
print("reference frames:", name, nf, "from", clip, r)
