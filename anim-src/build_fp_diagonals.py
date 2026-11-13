# build_fp_diagonals.py - the four first-person diagonal step dodges (ForwardLeft, ForwardRight, BackLeft, BackRight)
# for Skyrim SE, in Blender 5.2 + PyNifly (2026-11-13; the owner: "Build the first-person diagonals", after Nexus user
# 1m0ws asked for 8-way first-person dodging).
#
# In first person the four straight dodges play the game's own first-person clips (_1stperson\animations\dodgeback,
# dodgeleft, dodgeright, sneakrun_forwardroll). Those clips move almost nothing but the view: dodgeleft / dodgeright /
# dodgeback sway NPC Root (the camera's parent) about 12-20 units against and then into the dodge and tilt
# Camera1st [Cam1] 8-14 degrees; the forward roll holds a crouch (COM down, Cam1 at 82.6 instead of 120.5) and bobs
# the camera while the legs roll. The arms hold one still pose. A diagonal is the DIRECTION BLEND of its two
# neighbours, computed here frame by frame:
#
#   base(bone)  = halfway between the two clips' first frames (translation lerp, rotation slerp) - the held pose
#   delta_s(t)  = clip s at phase t relative to its own first frame (bone-local), sign kept continuous
#   pose(t)     = base + cos45 * delta_A(t) + cos45 * delta_B(t)      (rotation: base * delta_A^cos45 * delta_B^cos45)
#
# so the sway and the tilt point along the diagonal with the length of a straight dodge's (two perpendicular parts at
# cos45 each), the forward diagonals take half the forward roll's crouch, and a bone that holds still in both clips
# holds the same pose. The two clips are matched by PHASE (each resampled to the diagonal's length). Nothing of the
# game's clips is shipped: they are read at build time from the unpacked archive (SIMPLEDODGE_VANILLA_ANIMS, default
# ../_work/vanilla-anims), and the pose of every frame is computed and keyed anew.
#
#   ForwardLeft / ForwardRight: 31 frames, 1.0 s (the forward roll's length; the patch ends the dodge 0.4 s before
#                               the end, as for the forward roll)
#   BackLeft / BackRight:       28 frames, 0.9 s (the side and back clips' length; dodge ends 0.3 s before the end)
#
# Root motion: each clip carries "animmotion x y z" annotations equal to its FirstPerson~1 motion data (written by
# tools\patch_fp_diagonals.py: the third-person diagonal motion, sdge$0..3), so with Animation Motion Revolution the
# distance is the same as without it (the clip-motion gate checks this).
#
# Run (PowerShell or cmd):
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --factory-startup
#       --python-exit-code 1 --python build_fp_diagonals.py -- [build] [verify] [render] [install] [<Direction> ...]
# Stages: build   - FP armature, keyed action, markers, firstperson\StepDodge<Dir>.blend + .hkx (SE, 64-bit)
#         verify  - re-read the exported hkx: every track against the computed pose, annotations, duration
#         render  - the first-person camera's view (Cam1st, as the game places the camera) with the first-person
#                   arms skinned, over a floor grid and posts, travelling by the motion data; frames to
#                   firstperson\_frames\<Dir>. The straight directions (Forward Back Left Right) render too - from the
#                   game's clips, render only - so the review can set each diagonal beside its two neighbours.
#         install - copy the four hkx to dist\Meshes\Actors\Character\_1stperson\animations\TKDodge
# Then: py -3 make_fp_review_mp4.py (review videos), py -3 ..\tools\make_clip_motion.py (Shorter copies + check).
import bpy, sys, os, math, json, struct, shutil, addon_utils
from math import radians
from mathutils import Matrix, Vector, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, "firstperson")
SKEL_HKX = r"D:\Modlists\Njordlinger\mods\Pandora Behaviour Engine Plus\Pandora_Engine\Skyrim\Template\actors\character\_1stperson\characterassets\skeletonfirst.hkx"
VANILLA_ANIMS = os.environ.get("SIMPLEDODGE_VANILLA_ANIMS", os.path.join(REPO, "_work", "vanilla-anims", "meshes",
                               "actors", "character", "_1stperson", "animations"))
VANILLA_MESHES = os.environ.get("SIMPLEDODGE_VANILLA_MESHES", os.path.join(REPO, "_work", "vanilla-meshes", "meshes"))
BODY_DIR = r"D:\Modlists\Njordlinger\mods\Highly Improved Male Body Overhaul (HIMBO)\meshes\actors\character\character assets"
BODY_NIFS = ["1stpersonmalebody_1.nif", "1stpersonmalehands_1.nif"]
MD_DIR = os.path.join(REPO, "dist", "Nemesis_Engine", "mod", "sdge", "animationdatasinglefile", "FirstPerson~1")
INSTALL = os.path.join(REPO, "dist", "Meshes", "Actors", "Character", "_1stperson", "animations", "TKDodge")
FPS = 30
W45 = math.cos(math.pi / 4)

SOURCES = {"Forward": "sneakrun_forwardroll", "Back": "dodgeback", "Left": "dodgeleft", "Right": "dodgeright"}
MOTION = {"Forward": "791", "Back": "346", "Left": "347", "Right": "348",
          "ForwardLeft": "sdge$0", "ForwardRight": "sdge$1", "BackLeft": "sdge$2", "BackRight": "sdge$3"}
DIAGONALS = {"ForwardLeft": ("Forward", "Left", 31), "ForwardRight": ("Forward", "Right", 31),
             "BackLeft": ("Back", "Left", 28), "BackRight": ("Back", "Right", 28)}

addon_utils.enable("io_scene_nifly", default_set=True)
from io_scene_nifly.hkx import anim_skyrim as AS
from io_scene_nifly.hkx import anim_fo4 as AF
log = []
def say(*a):
    s = " ".join(str(x) for x in a); print(s); log.append(s)

# ------------------------------------------------------------------------------------------------ skeleton
def parse_skeleton(path):
    """The 99-bone first-person hkaSkeleton (skeletonfirst.hkx). Same 64-bit layout fix as build_stepdodge.py's
    parse_vanilla_skeleton: PyNifly's own reader returns 0 bones for these files."""
    data = open(path, "rb").read()
    secs = AS._parse_hkx_sections(data); ds = secs['__data__']; d = ds['offset']
    fx = AS._parse_local_fixups(data, ds)
    for rel, cls in AS._parse_virtual_fixups(data, ds, secs['__classnames__']['offset']):
        if cls != 'hkaSkeleton':
            continue
        s = d + rel
        cnt = lambda off: struct.unpack_from('<I', data, s + off + 8)[0]
        bones, lock = [], []
        bc = fx.get(rel + 48)
        for i in range(cnt(48)):
            br = bc + 16 * i
            bones.append(AS._read_null_string(data, d + fx[br]) if br in fx else "")
            lock.append(bool(data[d + br + 8]))
        if len(bones) != 99:
            continue
        sk = AF.Skeleton(name=AS._read_null_string(data, d + fx[rel + 24]), bones=bones, lock_translation=lock)
        pi = fx[rel + 32]
        sk.parents = [struct.unpack_from('<h', data, d + pi + 2 * i)[0] for i in range(cnt(32))]
        pc = fx[rel + 64]
        for i in range(cnt(64)):
            f = struct.unpack_from('<12f', data, d + pc + 0x30 * i)
            sk.reference_pose.append(AF.BonePose(list(f[0:3]), list(f[4:8]), list(f[8:11])))
        fc = fx.get(rel + 80)
        sk.reference_floats = [struct.unpack_from('<f', data, d + fc + 4 * i)[0] for i in range(cnt(80))] if fc is not None else []
        sc = fx.get(rel + 96)
        sk.float_slots = [AS._read_null_string(data, d + fx[sc + 8 * i]) for i in range(cnt(96))] if sc is not None else []
        return sk
    raise RuntimeError("no 99-bone hkaSkeleton in " + path)

VSK = parse_skeleton(SKEL_HKX)
BN = VSK.bones; IDX = {n: i for i, n in enumerate(BN)}; PAR = VSK.parents
assert "Camera1st [Cam1]" in IDX, "not the first-person skeleton"

def import_armature(name="FPStepDodge_Skeleton"):
    orig = AS.load_skyrim_skeleton
    AS.load_skyrim_skeleton = lambda p: VSK
    try:
        r = bpy.ops.import_scene.pynifly_hkx(filepath=SKEL_HKX, rename_bones=False, rename_bones_niftools=False,
                                             blender_xf=False, rotate_bones_pretty=False)
    finally:
        AS.load_skyrim_skeleton = orig
    arma = bpy.context.object
    assert arma and arma.type == 'ARMATURE', r
    arma.name = name
    arma['PYN_SKELETON_FILE'] = SKEL_HKX
    return arma

def q_of(r): return Quaternion((r[3], r[0], r[1], r[2]))
REST = [(Vector(p.translation), q_of(p.rotation)) for p in VSK.reference_pose]

def globals_of(L):
    """armature-space 4x4 per bone from parent-local (t, q)."""
    G = []
    for i, (t, q) in enumerate(L):
        m = Matrix.Translation(t) @ q.to_matrix().to_4x4()
        G.append(G[PAR[i]] @ m if PAR[i] >= 0 else m)
    return G
G0 = globals_of(REST)

# ------------------------------------------------------------------------------------------------ source clips
_CLIPS = {}
def clip(direction):
    """(frames, duration, [[(t, q)] per bone] per frame) of the game's first-person clip for a straight direction."""
    if direction in _CLIPS: return _CLIPS[direction]
    a = AS.load_skyrim_animation(os.path.join(VANILLA_ANIMS, SOURCES[direction] + ".hkx"))
    binding = list(a.track_to_bone_indices) or list(range(len(a.tracks)))
    assert len(binding) == len(BN), (direction, len(binding))
    frames = []
    for k in range(a.num_frames):
        L = list(REST)
        for tr, bi in enumerate(binding):
            L[bi] = (Vector(a.tracks[tr].translations[k]), q_of(a.tracks[tr].rotations[k]))
        frames.append(L)
    _CLIPS[direction] = (a.num_frames, a.duration, frames)
    say("source %-8s %s.hkx: %d frames, %.3f s" % (direction, SOURCES[direction], a.num_frames, a.duration))
    return _CLIPS[direction]

def sample(direction, u):
    """bone-local (t, q) list at phase u in [0, 1] (linear / slerp between the clip's frames)."""
    n, _, F = clip(direction)
    x = u * (n - 1); k = min(int(x), n - 2); f = x - k
    out = []
    for (ta, qa), (tb, qb) in zip(F[k], F[k + 1]):
        if qa.dot(qb) < 0: qb = -qb
        out.append((ta.lerp(tb, f), qa.slerp(qb, f)))
    return out

def qpow(q, w):
    axis, ang = q.to_axis_angle()
    return Quaternion(axis, ang * w)

class Design:
    """parts: [(direction, base weight, delta weight)]."""
    def __init__(self, name, parts, nf):
        self.name, self.parts, self.nf = name, parts, nf
        self.diagonal = len(parts) == 2
        self.md = MOTION[name]
        self.motion, self.md_text = read_motion(self.md)
        self.duration = (nf - 1) / FPS
        self._poses = None

    def poses(self):
        if self._poses: return self._poses
        firsts = {d: clip(d)[2][0] for d, _, _ in self.parts}
        # base: the weighted blend of the first frames
        base = []
        for i in range(len(BN)):
            t = Vector(); q = None; acc = 0.0
            for d, bw, _ in self.parts:
                ti, qi = firsts[d][i]
                t += ti * bw
                if q is None: q = qi.copy(); acc = bw
                else:
                    if q.dot(qi) < 0: qi = -qi
                    acc += bw; q = q.slerp(qi, bw / acc)
            base.append((t, q))
        prev = {}
        self._poses = []
        for f in range(self.nf):
            u = f / (self.nf - 1)
            L = []
            cur = {d: sample(d, u) for d, _, _ in self.parts}
            for i in range(len(BN)):
                t, q = base[i][0].copy(), base[i][1].copy()
                for d, _, dw in self.parts:
                    t0, q0 = firsts[d][i]
                    ts, qs = cur[d][i]
                    dq = q0.inverted() @ qs
                    p = prev.get((d, i))
                    if (p is None and dq.w < 0) or (p is not None and p.dot(dq) < 0): dq = -dq
                    prev[(d, i)] = dq
                    t += (ts - t0) * dw
                    q = q @ qpow(dq, dw)
                q.normalize()
                L.append((t, q))
            self._poses.append(L)
        return self._poses

    def root(self, f):
        """motion data root path (x, y) at frame f, linear like the game."""
        t = f / FPS
        keys = self.motion
        if t >= keys[-1][0]: return Vector((keys[-1][1], keys[-1][2], 0))
        for (t0, x0, y0), (t1, x1, y1) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                a = (t - t0) / (t1 - t0) if t1 > t0 else 1
                return Vector((x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, 0))
        return Vector((0, 0, 0))

    def annotations(self):
        out = [(0.0, "animmotion 0 0 0")]
        for t, xs, ys in self.md_text:
            out.append((t, "animmotion %s %s 0" % (xs, ys)))
        return out

def read_motion(md):
    lines = [l.strip() for l in open(os.path.join(MD_DIR, md + ".txt"), encoding="ascii").read().split("\n")]
    assert lines[0] == md, (md, lines[0])
    n = int(lines[2])
    keys, text = [(0.0, 0.0, 0.0)], []
    for l in lines[3:3 + n]:
        t, x, y, z = l.split(" ")
        keys.append((float(t), float(x), float(y)))
        text.append((float(t), x, y))
    return keys, text

DESIGNS = {d: Design(d, [(a, 0.5, W45), (b, 0.5, W45)], nf) for d, (a, b, nf) in DIAGONALS.items()}
REFERENCES = {d: Design(d, [(d, 1.0, 1.0)], clip(d)[0]) for d in SOURCES}

# ------------------------------------------------------------------------------------------------ build stage
def clear_scene():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    for a in list(bpy.data.actions): bpy.data.actions.remove(a)

def key_scene(D):
    """armature + motion-data root empty, every frame keyed from D.poses(); returns (arma, root empty)."""
    clear_scene()
    sc = bpy.context.scene
    sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = D.nf
    arma = import_armature()
    arma.data.display_type = 'STICK'
    mr = bpy.data.objects.new("MotionData_Root (preview travel)", None); sc.collection.objects.link(mr)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    for f in range(D.nf):
        mr.location = D.root(f); mr.keyframe_insert("location", frame=f + 1)
    arma.parent = mr
    action = bpy.data.actions.new(("FPStepDodge%s" if D.diagonal else "FPReference%s") % D.name)
    arma.animation_data_create(); arma.animation_data.action = action
    Cfix = {}
    worst = 0
    for b in arma.data.bones:
        i = IDX[b.name]; Cfix[i] = G0[i].inverted() @ b.matrix_local
        worst = max(worst, max(abs(Cfix[i][r][c] - (1 if r == c else 0)) for r in range(4) for c in range(4)))
    say(D.name, "bone-vs-skeleton rest frame max deviation:", round(worst, 5))
    prevq = {}
    for f, L in enumerate(D.poses()):
        G = globals_of(L)
        M = {i: G[i] @ Cfix[i] for i in Cfix}
        for pb in arma.pose.bones:
            i = IDX[pb.name]; b = pb.bone
            if b.parent:
                rest_rel = b.parent.matrix_local.inverted() @ b.matrix_local
                basis = rest_rel.inverted() @ (M[IDX[b.parent.name]].inverted() @ M[i])
            else:
                basis = b.matrix_local.inverted() @ M[i]
            loc, q, _ = basis.decompose()
            if pb.name in prevq and prevq[pb.name].dot(q) < 0: q = -q
            prevq[pb.name] = q
            pb.rotation_mode = 'QUATERNION'
            pb.location = loc; pb.rotation_quaternion = q
            pb.keyframe_insert("location", frame=f + 1); pb.keyframe_insert("rotation_quaternion", frame=f + 1)
    action.use_frame_range = True; action.frame_start = 1; action.frame_end = D.nf
    return arma, mr

def build(D):
    arma, mr = key_scene(D)
    sc = bpy.context.scene; action = arma.animation_data.action
    for t, name in D.annotations():
        fr = 1 + round(t * FPS)
        action.pose_markers.new(name).frame = fr
        sc.timeline_markers.new(name, frame=fr)
    bpy.context.view_layer.objects.active = arma; arma.select_set(True)
    os.makedirs(OUT, exist_ok=True)
    hkx = os.path.join(OUT, f"StepDodge{D.name}.hkx")
    orig_w = AS.write_skyrim_animation
    def w(path, anim, ptr_size=4):
        anim.original_skeleton_name = VSK.name
        return orig_w(path, anim, ptr_size=ptr_size)
    AS.write_skyrim_animation = w
    try:
        r = bpy.ops.export_scene.pynifly_hkx(filepath=hkx, game='SKYRIM_SE', fps=FPS, reference_skel=SKEL_HKX)
    finally:
        AS.write_skyrim_animation = orig_w
    say(D.name, "export:", r, os.path.getsize(hkx) if os.path.exists(hkx) else "MISSING")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"StepDodge{D.name}.blend"))

# ------------------------------------------------------------------------------------------------ verify stage
def verify(D):
    a = AS.load_skyrim_animation(os.path.join(OUT, f"StepDodge{D.name}.hkx"))
    src = AS.load_skyrim_animation(os.path.join(VANILLA_ANIMS, SOURCES[D.parts[0][0]] + ".hkx"))
    binding = list(a.track_to_bone_indices) or list(range(len(a.tracks)))
    P = D.poses()
    et = eq = 0.0; worst = None
    for k in range(min(a.num_frames, D.nf)):
        for tr, bi in enumerate(binding):
            t = Vector(a.tracks[tr].translations[k]); q = q_of(a.tracks[tr].rotations[k])
            dt = (t - P[k][bi][0]).length
            dq = math.degrees(q.rotation_difference(P[k][bi][1]).angle)
            dq = min(dq, 360 - dq)
            if dt > et: et = dt
            if dq > eq: eq = dq; worst = (k, BN[bi])
    cam = IDX["Camera1st [Cam1]"]
    tilt = max(math.degrees(P[0][cam][1].rotation_difference(P[k][cam][1]).angle) for k in range(D.nf))
    sway = max((P[k][0][0] - P[0][0][0]).length for k in range(D.nf))
    camz = [round(P[k][cam][0].z, 1) for k in range(0, D.nf, 5)]
    anns = [(round(x.time, 4), x.text) for x in a.annotations]
    want = [(round(t, 4), s) for t, s in D.annotations()]
    out = dict(name=D.name, duration=round(a.duration, 4), frames=a.num_frames, tracks=a.num_tracks,
               skeleton_name=a.original_skeleton_name, source_skeleton_name=src.original_skeleton_name,
               blend_hint=a.blend_hint, source_blend_hint=src.blend_hint,
               frames_match=a.num_frames == D.nf, tracks_equal_skeleton=a.num_tracks == len(BN),
               max_track_translation_error=round(et, 4), max_track_rotation_error_deg=round(eq, 4), worst=worst,
               annotations=anns, annotations_match=len(anns) == len(want) and all(
                   abs(x[0] - y[0]) < 0.002 and x[1] == y[1] for x, y in zip(anns, want)),
               camera_tilt_max_deg=round(tilt, 2), root_sway_max=round(sway, 2), cam1_z_every_5=camz,
               motion_data=D.md, motion_end=D.motion[-1])
    ok = (out["frames_match"] and out["tracks_equal_skeleton"] and et < 0.05 and eq < 0.2 and out["annotations_match"]
          and abs(out["duration"] - D.duration) < 0.002)
    out["PASS"] = ok
    json.dump(out, open(os.path.join(OUT, f"_verify_{D.name}.json"), "w"), indent=1)
    say(json.dumps(out))
    if not ok: raise SystemExit("verify FAILED for " + D.name)

def verify_reference(D):
    """the straight directions' numbers, for the log: what a diagonal is being compared with."""
    P = D.poses(); cam = IDX["Camera1st [Cam1]"]
    tilt = max(math.degrees(P[0][cam][1].rotation_difference(P[k][cam][1]).angle) for k in range(D.nf))
    sway = max((P[k][0][0] - P[0][0][0]).length for k in range(D.nf))
    say("reference %-8s tilt %.1f deg, root sway %.1f, Cam1 z %s" % (D.name, tilt, sway,
        [round(P[k][cam][0].z, 1) for k in range(0, D.nf, 5)]))

# ------------------------------------------------------------------------------------------------ render stage
def _import_skinned(path, arma):
    before = set(bpy.data.objects)
    for o in bpy.context.selected_objects: o.select_set(False)
    bpy.context.view_layer.objects.active = None
    bpy.ops.import_scene.pynifly(filepath=path, blender_xf=False, rename_bones=False, rename_bones_niftools=False,
                                 rotate_bones_pretty=False, import_animations=False, import_collisions=False,
                                 import_tris=False, import_shapekeys=False)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = []
    for o in new:
        if o.type == 'MESH':
            mw = o.matrix_world.copy()
            for m in o.modifiers:
                if m.type == 'ARMATURE': m.object = arma
            o.parent = arma; o.parent_type = 'OBJECT'
            o.matrix_parent_inverse = Matrix.Identity(4); o.matrix_basis = mw
            meshes.append(o)
    for o in new:
        if o.type == 'ARMATURE': bpy.data.objects.remove(o)
        elif o.type == 'EMPTY' and not o.children: bpy.data.objects.remove(o)
    return meshes

def _import_static(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.pynifly(filepath=path, blender_xf=False, rename_bones=False, rename_bones_niftools=False,
                                 rotate_bones_pretty=False, import_animations=False, import_collisions=False,
                                 import_tris=False, import_shapekeys=False)
    new = [o for o in bpy.data.objects if o not in before]
    keep = [o for o in new if o.type == 'MESH']
    for o in keep:
        mw = o.matrix_world.copy()
        for m in list(o.modifiers): o.modifiers.remove(m)
        o.parent = None; o.matrix_world = mw
    for o in new:
        if o not in keep: bpy.data.objects.remove(o)
    return keep

def render(D):
    arma, mr = key_scene(D)
    sc = bpy.context.scene
    sc.frame_set(1)
    arma.data.pose_position = 'REST'
    mr_loc = mr.location.copy(); mr.animation_data_clear(); mr.location = (0, 0, 0)
    body = []
    for nif in BODY_NIFS:
        p = os.path.join(BODY_DIR, nif)
        if not os.path.exists(p): p = os.path.join(VANILLA_MESHES, "actors", "character", "character assets", nif)
        body += _import_skinned(p, arma)
    arma.data.pose_position = 'POSE'
    for f in range(D.nf):
        mr.location = D.root(f); mr.keyframe_insert("location", frame=f + 1)
    sc.frame_set(1)
    # an iron sword in the right hand (the 1hm graph's view; render only)
    sword = os.path.join(VANILLA_MESHES, "weapons", "iron", "longsword.nif")
    if os.path.exists(sword):
        pb = arma.pose.bones["Weapon"]; W = arma.matrix_world @ pb.matrix
        for o in _import_static(sword):
            local = o.matrix_world.copy()
            o.parent = arma; o.parent_type = 'BONE'; o.parent_bone = "Weapon"
            o.matrix_world = W @ local
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'
    sh.show_shadows = False; sh.show_cavity = True; sh.cavity_type = 'WORLD'
    sh.background_type = 'VIEWPORT'; sh.background_color = (0.55, 0.62, 0.70)
    bodymat = bpy.data.materials.new("body"); bodymat.diffuse_color = (0.74, 0.62, 0.52, 1)
    for o in body: o.data.materials.clear(); o.data.materials.append(bodymat)
    # floor with a 40-unit grid and a ring of posts, so the view's travel and tilt read
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.05)); fl = bpy.context.object; fl.scale = (3000, 3000, 1)
    m = bpy.data.materials.new("floor"); m.diffuse_color = (0.47, 0.45, 0.42, 1); fl.data.materials.append(m)
    gm = bpy.data.materials.new("grid"); gm.diffuse_color = (0.30, 0.29, 0.27, 1)
    for g in range(-1200, 1201, 40):
        for sx, sy, loc in ((0.8, 2400, (g, 0, 0)), (2400, 0.8, (0, g, 0))):
            bpy.ops.mesh.primitive_cube_add(size=1, location=loc); c = bpy.context.object
            c.scale = (sx, sy, 0.15); c.data.materials.append(gm)
    pm = bpy.data.materials.new("post"); pm.diffuse_color = (0.62, 0.32, 0.22, 1)
    pm2 = bpy.data.materials.new("post2"); pm2.diffuse_color = (0.25, 0.40, 0.62, 1)
    for k in range(-6, 7):
        for y, mat in ((420, pm), (900, pm2)):
            bpy.ops.mesh.primitive_cube_add(size=1, location=(k * 80, y, 90)); c = bpy.context.object
            c.scale = (14, 14, 180); c.data.materials.append(mat)
    # the first-person camera: Camera1st [Cam1]'s frame each frame (+Y forward, +Z up), riding the motion data
    cd = bpy.data.cameras.new("Cam1st"); cd.lens_unit = 'FOV'; cd.sensor_fit = 'HORIZONTAL'
    cd.angle = radians(80); cd.clip_start = 1.0; cd.clip_end = 6000
    co = bpy.data.objects.new("Cam1st", cd); sc.collection.objects.link(co); sc.camera = co
    cam = IDX["Camera1st [Cam1]"]
    R = Matrix.Rotation(radians(90), 4, 'X')
    for f, L in enumerate(D.poses()):
        G = globals_of(L)
        co.matrix_world = Matrix.Translation(D.root(f)) @ G[cam] @ R
        co.keyframe_insert("location", frame=f + 1); co.keyframe_insert("rotation_euler", frame=f + 1)
    sc.render.resolution_x = 640; sc.render.resolution_y = 360; sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    frames_dir = os.path.join(OUT, "_frames", D.name); os.makedirs(frames_dir, exist_ok=True)
    for f in range(1, D.nf + 1):
        sc.frame_set(f)
        sc.render.filepath = os.path.join(frames_dir, f"Cam1st_{f:03d}.png")
        bpy.ops.render.render(write_still=True)
    say(D.name, "rendered", D.nf, "frames ->", frames_dir)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"_preview_{D.name}.blend"))

def install(D):
    os.makedirs(INSTALL, exist_ok=True)
    src = os.path.join(OUT, f"StepDodge{D.name}.hkx"); dst = os.path.join(INSTALL, f"StepDodge{D.name}.hkx")
    shutil.copyfile(src, dst)
    say(D.name, "installed", dst)

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stages = [a_ for a_ in args if a_ in ("build", "verify", "render", "install")] or ["build", "verify", "render", "install"]
    names = [a_ for a_ in args if a_ in DESIGNS or a_ in REFERENCES] or list(DESIGNS) + list(REFERENCES)
    for n in names:
        D = DESIGNS.get(n) or REFERENCES[n]
        for st in stages:
            if n in REFERENCES:
                if st == "render": render(D)
                elif st == "verify": verify_reference(D)
                continue
            {"build": build, "verify": verify, "render": render, "install": install}[st](D)
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "_log_%s_%s.txt" % ("_".join(stages), "_".join(names) if len(names) <= 4 else "all")), "w").write("\n".join(log))
