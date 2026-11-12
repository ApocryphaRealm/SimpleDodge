# showcase_render.py - renders a dodge clip for the Nexus page: the character in a full armour set (body, cuirass,
# boots, gauntlets, helmet from the load order) on a lit floor, EEVEE, one three-quarter camera that rides the clip's
# root, written as PNG frames to _showcase\<Design>\ for make_showcase_gif. The owner, 2026-11-11: "Would it be possible
# to play those GIFs with a loaded character's body with armor on?"
# Run: blender --background --factory-startup --python showcase_render.py -- <Design> [<Design> ...]
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_stepdodge as B
from mathutils import Matrix, Vector
from math import radians

# Vanilla Steel Armor (the owner, 2026-11-11: "Don't do Nordic Ebony, since we don't own its assets. Just do a vanilla
# armor set."), unpacked from Skyrim - Meshes0.bsa / Skyrim - Textures2.bsa into _showcase_assets (git-ignored -
# Bethesda's files are never committed).
ARMOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_showcase_assets", "meshes", "armor", "steel")
# vanilla pieces only: the steel cuirass and gauntlets carry their own body and hand parts (no third-party body mesh)
PIECES = [os.path.join(ARMOR_DIR, n) for n in
          ("cuirass_1.nif", "boots_1.nif", "gauntlets_1.nif", "helmet_1.nif")]
W, H = 720, 480
TOP = False
FOLLOW = False   # --follow: top-down, riding the character (the Nexus page GIFs)

def dress(arma):
    arma.data.pose_position = 'REST'
    for nif in PIECES:
        before = set(bpy.data.objects)
        for o in bpy.context.selected_objects: o.select_set(False)
        bpy.context.view_layer.objects.active = None
        bpy.ops.import_scene.pynifly(filepath=nif, blender_xf=False, rename_bones=False, rename_bones_niftools=False,
                                     rotate_bones_pretty=False, import_animations=False, import_collisions=False,
                                     import_tris=False, import_shapekeys=False)
        new = [o for o in bpy.data.objects if o not in before]
        for o in new:
            if o.type == 'MESH':
                mw = o.matrix_world.copy()
                for m in o.modifiers:
                    if m.type == 'ARMATURE': m.object = arma
                o.parent = arma; o.parent_type = 'OBJECT'
                o.matrix_parent_inverse = Matrix.Identity(4); o.matrix_basis = mw
                imgs = [n.image.name for mat in o.data.materials if mat and mat.use_nodes
                        for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
                B.say("dressed", os.path.basename(nif), o.name, "textures:", imgs[:3])
                if not any(bpy.data.images[i].has_data or bpy.data.images[i].size[0] for i in imgs):
                    skin = bpy.data.materials.get("Skin") or bpy.data.materials.new("Skin")
                    skin.diffuse_color = (0.62, 0.47, 0.38, 1)
                    if skin.node_tree and "Principled BSDF" in skin.node_tree.nodes:
                        skin.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.62, 0.47, 0.38, 1)
                        skin.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
                    o.data.materials.clear(); o.data.materials.append(skin)   # no skin texture loaded: plain skin tone
        for o in new:
            if o.type == 'ARMATURE': bpy.data.objects.remove(o)
            elif o.type == 'EMPTY' and not o.children: bpy.data.objects.remove(o)
    arma.data.pose_position = 'POSE'

def stage(D, mr):
    sc = bpy.context.scene
    T = D.root(D.nf - 1)
    for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        try: sc.render.engine = eng; break
        except TypeError: pass
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'AgX' if 'AgX' in [v.identifier for v in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
    # floor: large plane, stone-grey with a faint checker so the travel reads
    bpy.ops.mesh.primitive_plane_add(size=1, location=(T.x / 2, T.y / 2, 0)); fl = bpy.context.object
    fl.scale = (1600, 1600, 1)
    m = bpy.data.materials.new("floor"); m.use_nodes = True; nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]; ch = nt.nodes.new("ShaderNodeTexChecker"); tc = nt.nodes.new("ShaderNodeTexCoord")
    ch.inputs["Scale"].default_value = 64.0
    ch.inputs["Color1"].default_value = (0.20, 0.19, 0.18, 1); ch.inputs["Color2"].default_value = (0.25, 0.24, 0.22, 1)
    nt.links.new(tc.outputs["UV"], ch.inputs["Vector"]); nt.links.new(ch.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.85
    fl.data.materials.append(m)
    # light: warm key sun, cool fill, dim world
    sun = bpy.data.objects.new("Key", bpy.data.lights.new("Key", 'SUN')); sc.collection.objects.link(sun)
    sun.data.energy = 3.5; sun.data.color = (1.0, 0.93, 0.82); sun.rotation_euler = (radians(50), radians(10), radians(140))
    fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", 'SUN')); sc.collection.objects.link(fill)
    fill.data.energy = 1.0; fill.data.color = (0.75, 0.82, 1.0); fill.rotation_euler = (radians(65), 0, radians(-60))
    if sc.world is None: sc.world = bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.09, 0.095, 0.11, 1)
    sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    # camera: three-quarter front, riding the root so the body stays framed and the floor moves under it
    cd = bpy.data.cameras.new("Show"); cd.lens = 50
    cam = bpy.data.objects.new("Show", cd); sc.collection.objects.link(cam); cam.parent = mr
    cam.location = (230, 330, 120)
    d = Vector((0, 0, 70)) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    if TOP:
        # the owner, 2026-11-11: "It's hard to see what's happening from that angle. I'd rather see it from the top
        # down." Straight down, fixed above the dodge (not riding the root) so the whole path and every foot plant
        # shows; facing direction (+Y) points up the picture.
        cam.parent = None; cd.type = 'ORTHO'; cd.clip_start = 1.0; cd.clip_end = 5000.0   # default clip_end 100 cut it all
        span = max(abs(T.x), abs(T.y)) + 100
        for L in bpy.data.objects:                       # sun high overhead: short shadows that do not cross the path
            if L.type == 'LIGHT' and L.name == "Key": L.rotation_euler = (radians(18), radians(8), radians(140))
        cd.ortho_scale = span
        cam.location = (T.x / 2, T.y / 2, 1200); cam.rotation_euler = (0, 0, 0)
        sc.render.resolution_x = sc.render.resolution_y = 720
        if FOLLOW:
            # 2026-11-11, the Nexus page: framing the whole path left the body a small figure in a big floor, at any
            # crop. Ride the character's position (not its turn) so the body stays large and the floor slides under it.
            cd.ortho_scale = 170
            cam.location = (0, 0, 1200)
            c = cam.constraints.new('COPY_LOCATION'); c.target = mr; c.use_z = False

def blank_check(png):
    # 2026-11-11: the top-down camera's default clip_end (100) cut the whole scene and every frame came out as flat
    # background - a full clip rendered before anyone looked. The first frame must hold more than one colour, or stop.
    im = bpy.data.images.load(png); px = im.pixels[:]; bpy.data.images.remove(im)
    lum = [px[i] + px[i + 1] + px[i + 2] for i in range(0, len(px), 4 * 97)]
    if max(lum) - min(lum) < 0.05:
        raise SystemExit(f"BLANK FRAME {png}: one flat colour - check the camera's clip range and framing")

def render(D):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(B.OUT, f"{D.file}.blend"))
    arma = bpy.data.objects["StepDodge_Skeleton"]; mr = arma.parent
    dress(arma)
    stage(D, mr)
    out = os.path.join(B.OUT, "_showcase_follow" if FOLLOW else "_showcase_top" if TOP else "_showcase", D.name); os.makedirs(out, exist_ok=True)
    sc = bpy.context.scene
    for f in range(1, D.nf + 1):
        sc.frame_set(f); sc.render.filepath = os.path.join(out, f"{f:03d}.png")
        bpy.ops.render.render(write_still=True)
        if f == 1: blank_check(sc.render.filepath)
    B.say("showcase", D.name, D.nf, "frames ->", out)

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["Forward"]
    FOLLOW = "--follow" in args
    TOP = "--top" in args or FOLLOW
    for k in [a for a in args if a not in ("--top", "--follow")]: render(B.DESIGNS[k])
