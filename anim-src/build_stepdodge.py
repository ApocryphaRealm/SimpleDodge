# build_stepdodge.py - builds our own four step dodges (Left, Right, Forward, Back) for Skyrim SE from scratch,
# in Blender 5.2 + PyNifly.
#
# Everything here is procedural: the pose of every frame is computed from our own key curves (COM path, foot plants,
# lean, guard), solved with our own two-bone IK, and keyed onto an armature built from the vanilla SE skeleton.hkx.
# No existing dodge animation is read for motion - only each reference clip's length and annotation list are reused
# so the existing dodge behaviour patch and its motion data still fit.
# Right is the Left design mirrored across X in world space (feet, body path, lean, guard offsets), laid onto the
# Right motion data; Forward (a lunge into a short run-out) and Back (a hop-step) are their own designs.
#
# Run (PowerShell or cmd):
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --factory-startup
#       --python-exit-code 1 --python build_stepdodge.py -- <stage> [...] [<Direction> ...]
# Stages: build   - armature, keyed action, markers, StepDodge<Dir>.blend + StepDodge<Dir>.hkx (SE, 64-bit)
#         verify  - re-import the exported hkx onto a fresh armature and compare with the skeleton + reference
#         render  - skin the HIMBO body meshes from the load order and render the preview frames
# Directions: Left Right Forward Back (default: all four). Stages default to all three.
#
# Coordinates are Skyrim's: +Y forward, +X the actor's right, +Z up, game units (1 unit ~ 1.43 cm). Each clip is
# in place at NPC Root [Root]; travel comes from the behaviour's animationdatasinglefile motion data, so every
# world-space plant below is turned into root-local space by subtracting the motion-data root path R(t).
import bpy, sys, os, math, json, struct, addon_utils
from math import radians
from mathutils import Matrix, Vector, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE
SKEL_HKX = r"D:\Modlists\Njordlinger\mods\Pandora Behaviour Engine Plus\Pandora_Engine\Skyrim\Template\actors\character\character assets\skeleton.hkx"
# The installed reference clips (the TKDodge clip folder name is the compatibility path); override with SIMPLEDODGE_REF_DIR.
REF_DIR = os.environ.get("SIMPLEDODGE_REF_DIR",
                         r"D:\Modlists\Njordlinger\mods\test Simple Dodge\Meshes\Actors\Character\animations\TKDodge")
BODY_DIR = r"D:\Modlists\Njordlinger\mods\Highly Improved Male Body Overhaul (HIMBO)\meshes\actors\character\character assets"
BODY_NIFS = ["malebody_1.nif", "malehands_1.nif", "malefeet_1.nif"]
FPS = 30

# Motion data (animationdatasinglefile DefaultMale~1, same in DefaultFemale~1): duration, then (time, x, y) keys.
# Annotations of the current clips: names and times kept identical (they mirror the motion data).
SPEC = {
    "Left": dict(md="sdge$2", duration=0.7, motion=[(0.0, 0, 0), (0.06667, -23.0, 0), (0.1, -45.0, 0),
        (0.26667, -114.9, 0), (0.53333, -214.1, 0), (0.63333, -244.3, 0), (0.66667, -250.0, 0), (0.7, -251.7, 0)],
        ann=[(0.0, "animmotion 0 0 0"), (0.0667, "animmotion -23.0 0 0"), (0.1, "animmotion -45.0 0 0"),
             (0.2667, "animmotion -114.9 0 0"), (0.5333, "animmotion -214.1 0 0"), (0.6333, "animmotion -244.3 0 0"),
             (0.6667, "animmotion -250.0 0 0"), (0.7, "animmotion -251.7 0 0")]),
    "Right": dict(md="sdge$3", duration=0.7, motion=[(0.0, 0, 0), (0.06667, 28.6, 0), (0.1, 50.0, 0),
        (0.23333, 102.0, 0), (0.53333, 224.5, 0), (0.66667, 251.2, 0), (0.7, 251.2, 0)],
        ann=[(0.0, "animmotion 0 0 0"), (0.0667, "animmotion 28.6 0 0"), (0.1, "animmotion 50.0 0 0"),
             (0.2333, "animmotion 102.0 0 0"), (0.5333, "animmotion 224.5 0 0"), (0.6667, "animmotion 251.2 0 0"),
             (0.7, "animmotion 251.2 0 0")]),
    "Forward": dict(md="sdge$0", duration=0.866667, motion=[(0.0, 0, 0), (0.0666667, -2.44943e-07, 12.963),
        (0.133333, -1.68889e-06, 38.1847), (0.233333, -4.79072e-06, 90.7585), (0.366667, -1.05933e-05, 178.629),
        (0.533333, -1.91211e-05, 291.939), (0.633333, -2.41794e-05, 348.552), (0.7, -2.72645e-05, 376.935),
        (0.766667, -2.99817e-05, 395.209), (0.866667, -3.30838e-05, 409.283)],
        ann=[(0.0, "animmotion 0 0 0"), (0.0667, "animmotion 0 12.963 0"), (0.1333, "animmotion 0 38.1847 0"),
             (0.2333, "animmotion 0 90.7585 0"), (0.3667, "animmotion 0 178.629 0"), (0.5333, "animmotion 0 291.939 0"),
             (0.6333, "animmotion 0 348.552 0"), (0.7, "animmotion 0 376.935 0"), (0.7667, "animmotion 0 395.209 0"),
             (0.8667, "animmotion 0 409.283 0")]),
    "Back": dict(md="sdge$1", duration=0.8, motion=[(0.0, 0, 0), (0.1, 0, -38.0), (0.16667, 0, -78.5),
        (0.26667, 0, -129.6), (0.46667, 0, -223.2), (0.53333, 0, -250.8), (0.56667, 0, -265.2), (0.6, 0, -278.6),
        (0.7, 0, -296.5), (0.8, 0, -300.0)],
        ann=[(0.0, "animmotion 0 0 0"), (0.1, "animmotion 0 -38.0 0"), (0.1667, "animmotion 0 -78.5 0"),
             (0.2667, "animmotion 0 -129.6 0"), (0.4667, "animmotion 0 -223.2 0"), (0.5333, "animmotion 0 -250.8 0"),
             (0.5667, "animmotion 0 -265.2 0"), (0.6, "animmotion 0 -278.6 0"), (0.7, "animmotion 0 -296.5 0"),
             (0.8, "animmotion 0 -300.0 0")]),
}

# Rolls (the owner, 2026-11-11: "make a simple roll dodge for testing that can be replaced by other mods"): the four
# vanilla-named roll clips the dodge behaviour plays when step dodge is off. Length and annotation list are those
# of the clips the package carried before, so the behaviour and any roll replacer still fit; the
# motion is ours. Motion = the annotations' animmotion travel (those clips have no motion-data entry of their own).
ROLL_ANN = {
    "RollLeft": ("dodgeleft", 0.7, [(0.0, -0.0, 0), (0.0333, -5.33511, 0), (0.1, -28.8548, 0), (0.2, -68.0616, 0),
        (0.3333, -111.319, 0), (0.5333, -179.919, 0), (0.6, -199.692, 0), (0.6667, -210.336, 0)]),
    "RollRight": ("dodgeright", 0.7, [(0.0, 0, 0), (0.0333, 5.33511, 0), (0.1, 28.8548, 0), (0.2, 68.0616, 0),
        (0.3333, 111.319, 0), (0.5333, 179.919, 0), (0.6, 199.692, 0), (0.6667, 210.336, 0)]),
    "RollBack": ("dodgeback", 0.8, [(0.0, 0, 0), (0.1, 0, -3.90818), (0.2, 0, -17.8417), (0.3, 0, -43.0991),
        (0.5667, 0, -152.089), (0.7, 0, -187.724), (0.8, 0, -202.3), (0.9, 0, -207.07)]),
    "RollForward": ("sneakrun_forwardroll", 0.866667, [(0.0, 0, 0), (0.0667, 0, 12.963), (0.1333, 0, 38.1847),
        (0.2333, 0, 90.7585), (0.3667, 0, 178.629), (0.5333, 0, 291.939), (0.6333, 0, 348.552), (0.7, 0, 376.935),
        (0.7667, 0, 395.209), (0.8667, 0, 409.283)]),
}
def _g(v): return ("%.6g" % v) if v else "0"
for _n, (_file, _dur, _keys) in ROLL_ANN.items():
    SPEC[_n] = dict(md=None, file=_file, duration=_dur,
        motion=[(t, x, y) for t, x, y in _keys if t <= _dur + 1e-6],
        ann=[(t, "animmotion %s %s 0" % (_g(x), _g(y))) for t, x, y in _keys])

addon_utils.enable("io_scene_nifly", default_set=True)
from io_scene_nifly.hkx import anim_skyrim as AS
from io_scene_nifly.hkx import anim_fo4 as AF
log = []
def say(*a):
    s = " ".join(str(x) for x in a); print(s); log.append(s)

# ------------------------------------------------------------------------------------------------ skeleton
def parse_vanilla_skeleton(path):
    """The vanilla SE skeleton.hkx carries a ragdoll and two hkaSkeletons, and its 64-bit hkaSkeleton fields sit 8
    bytes later than PyNifly's reader expects (name +24, parents +32, bones +48, pose +64, floats +80, slots +96), so
    PyNifly returns 0 bones for it. Read the 99-bone skeleton ourselves with PyNifly's section/fixup helpers."""
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

VSK = parse_vanilla_skeleton(SKEL_HKX)

def import_armature(name="StepDodge_Skeleton"):
    """Build the armature with PyNifly's own HKX skeleton importer (so it carries PYN_HKX_BONES / game / pointer
    size exactly as PyNifly's exporter wants), feeding it the skeleton we parsed."""
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

# Rest global transforms (armature space) straight from the skeleton.
def rest_globals():
    G = []
    for i, p in enumerate(VSK.reference_pose):
        t, r = p.translation, p.rotation
        m = Matrix.Translation(Vector(t)) @ Quaternion((r[3], r[0], r[1], r[2])).to_matrix().to_4x4()
        par = VSK.parents[i]
        assert par < i
        G.append(G[par] @ m if par >= 0 else m)
    return G
G0 = rest_globals()
BN = VSK.bones; IDX = {n: i for i, n in enumerate(BN)}; PAR = VSK.parents
L0 = [(G0[PAR[i]].inverted() @ G0[i]) if PAR[i] >= 0 else G0[i].copy() for i in range(len(BN))]
B0 = [g.to_3x3() for g in G0]
def P0(name): return G0[IDX[name]].translation.copy()

# ------------------------------------------------------------------------------------------------ curves
def mono(keys, f):
    """Monotone cubic (Fritsch-Carlson) through (frame, value) keys: eased, never overshoots a key."""
    xs = [k[0] for k in keys]; ys = [k[1] for k in keys]
    if f <= xs[0]: return ys[0]
    if f >= xs[-1]: return ys[-1]
    n = len(xs)
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [d[0]] + [0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2 for i in range(1, n - 1)] + [d[-1]]
    m[0] = 0.0; m[-1] = 0.0                    # ease in and out at the ends
    for i in range(n - 1):
        if d[i] == 0: m[i] = m[i + 1] = 0.0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            s = a * a + b * b
            if s > 9: t = 3 / math.sqrt(s); m[i] = t * a * d[i]; m[i + 1] = t * b * d[i]
    for i in range(n - 1):
        if xs[i] <= f <= xs[i + 1]:
            h = xs[i + 1] - xs[i]; t = (f - xs[i]) / h
            h00 = 2*t**3 - 3*t**2 + 1; h10 = t**3 - 2*t**2 + t; h01 = -2*t**3 + 3*t**2; h11 = t**3 - t**2
            return h00 * ys[i] + h10 * h * m[i] + h01 * ys[i + 1] + h11 * h * m[i + 1]

def Rax(axis, deg):
    return Matrix.Rotation(radians(deg), 3, axis)

# ------------------------------------------------------------------------------------------------ the motion
# All positions WORLD (floor) space; root-local = world - R(f). Every design ends in the same combat stance:
# COM root-local (0, 0.5, 64.5), hips/spine at (pitch -2 / -3, no roll or yaw), left ankle over (-14, +4),
# right ankle over (+14, -5), guard at LH_GUARD / RH_GUARD - and starts in it too, so all four blend alike.
LH_GUARD = Vector((-10.0, 14.0, 97.0)); RH_GUARD = Vector((10.0, 12.0, 95.0))

class Design:
    def __init__(self, name, K):
        sp = SPEC[name]
        self.name, self.K = name, K
        self.duration = sp["duration"]; self.motion = sp["motion"]; self.ann = sp["ann"]
        self.nf = round(self.duration * FPS) + 1
        if sp.get("file"):                      # a roll: vanilla-named clip one folder up from TKDodge\
            self.file = sp["file"]; self.ref = os.path.join(os.path.dirname(REF_DIR), self.file + ".hkx")
        else:
            self.file = f"StepDodge{name}"; self.ref = os.path.join(REF_DIR, f"StepDodge{name}.hkx")
    roll = False
    def root(self, f):
        """Motion-data root travel (linear between keys, as the engine reads it)."""
        t = f / FPS; m = self.motion
        for (t0, x0, y0), (t1, x1, y1) in zip(m, m[1:]):
            if t <= t1:
                u = (t - t0) / (t1 - t0); return Vector((x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, 0))
        return Vector((m[-1][1], m[-1][2], 0))
    def v(self, name, f):
        return mono(self.K[name], f) if name in self.K else 0.0
    def com_local(self, f):
        return Vector((self.v("com_off_x", f), self.v("com_off_y", f), self.v("com_z", f)))
    def foot(self, pre, f):
        return self.v(pre + "_x", f), self.v(pre + "_y", f), self.v(pre + "_lift", f), self.v(pre + "_heel", f)

class Mirror(Design):
    """The source design mirrored across X (the actor's left/right) in WORLD space, laid onto this direction's own
    motion data: feet, body path and lean are mirrored, lateral distances scaled to this clip's travel. The fore-aft
    (y) stance offsets stay with each foot's own side, so start and end stance are the same as every other clip."""
    def __init__(self, name, src):
        super().__init__(name, {})
        self.src = src
        self.s = abs(self.motion[-1][1]) / abs(src.motion[-1][1])
    NEG = {"hip_roll", "hip_yaw", "spine_roll", "com_off_x"}
    def v(self, name, f):
        S = self.src
        if name in self.NEG: return -S.v(name, f)
        if name.startswith(("lf_", "rf_")): return S.v(("rf_" if name.startswith("lf_") else "lf_") + name[3:], f)
        if name.startswith(("lh_", "rh_")):
            o = ("rh_" if name.startswith("lh_") else "lh_") + name[3:]
            return -S.v(o, f) if name.endswith("dx") else S.v(o, f)
        return S.v(name, f)
    def com_local(self, f):
        S = self.src
        w = S.root(f) + Vector((S.v("com_off_x", f), S.v("com_off_y", f), 0))
        loc = Vector((-w.x * self.s, w.y, 0)) - self.root(f)
        loc.z = S.v("com_z", f)
        return loc
    def foot(self, pre, f):
        other = "rf" if pre == "lf" else "lf"
        x, y, lift, heel = self.src.foot(other, f)
        dy = 32.0 if pre == "lf" else -32.0        # staggered stance: left foot y +16, right -16 (owner, 2026-11-11)
        return -x * self.s, y + dy, lift, heel

def gait(pre, plants, lifts):
    """Foot curves from a plant list: plants = [(first frame, last frame, x, y, toe-off heel degrees)], lifts =
    swing heights between consecutive plants. Swings ease in and out; the heel peels up through the last frames of
    each plant (pivot on the ball), toes lift a touch before the next contact."""
    X, Y, L, H = {}, {}, {}, {}
    for i, (fs, fe, x, y, toe) in enumerate(plants):
        X[fs] = X[fe] = x; Y[fs] = Y[fe] = y; L[fs] = L[fe] = 0.0
        H[fs] = 0.0
        if i < len(plants) - 1:
            nfs = plants[i + 1][0]
            if fe - 2 > fs: H[fe - 2] = 0.0
            H[fe] = toe; H[fe + (nfs - fe) * 0.35] = toe * 0.4
            if nfs - 1 > fe + (nfs - fe) * 0.35 + 0.5: H[nfs - 1] = -2.0    # heel-first touch; -4 lifted the toe ~5 units (v3)
            L[(fe + nfs) / 2] = lifts[i]
        else:
            H[fe] = 0.0
    srt = lambda d: sorted(d.items())
    return {pre + "_x": srt(X), pre + "_y": srt(Y), pre + "_lift": srt(L), pre + "_heel": srt(H)}

LEFT_V1 = Design("Left", dict(
    # body (COM) offset from the capsule (+ = to the actor's right of the root). It holds still while the capsule
    # starts (anticipation), is thrown left by the push, leads a little while braking, and settles on the root.
    com_off_x=[(0, 0), (1, 11), (2, 21), (3, 29), (4, 32), (6, 22), (9, 2), (13, -12), (17, -9), (21, 0)],
    com_off_y=[(0, 0.5), (4, -1), (12, 1.5), (21, 0.5)],
    # height: dip (load) -> push extension -> low hop apex -> landing compression -> back to the combat stance
    com_z=[(0, 64.5), (2, 60), (4, 61.5), (8, 64.5), (13, 58.5), (15, 56), (18, 61.5), (21, 64.5)],
    hip_roll=[(0, 0), (2, 2.5), (5, -5), (9, -7), (13, -3), (16, 2), (19, 0.5), (21, 0)],    # about +Y; - leans left
    hip_pitch=[(0, -2), (2, -5), (5, -3), (9, -2), (14, -5), (18, -3), (21, -2)],           # about +X; - leans forward
    hip_yaw=[(0, 0), (3, -2), (8, 4), (14, 2), (21, 0)],                                     # about +Z
    spine_roll=[(0, 0), (2, 2), (5, -5), (9, -7), (13, -3), (16, 2), (19, 0), (21, 0)],
    spine_pitch=[(0, -3), (2, -5), (13, -5), (21, -3)],
    # feet: anchor = where the flat foot's ankle sits over the floor; lift = height above it; heel = toe-down degrees
    # (pivot at the ball while > 0, at the heel while < 0)
    lf_x=[(0, -14), (2, -14), (3, -20), (8, -130), (13, -232), (15, -257), (17, -265.7), (21, -265.7)],
    lf_y=[(0, 4), (2, 4), (8, 2), (13, 3), (21, 4)],
    lf_lift=[(0, 0), (1, 0), (2, 0.5), (4, 5), (7, 9), (10, 7), (12, 2.5), (13, 0), (21, 0)],
    lf_heel=[(0, 0), (1, 5), (2, 14), (3, 10), (6, 0), (11, -3), (13, 0), (21, 0)],
    rf_x=[(0, 14), (4, 14), (5, 8), (10, -110), (15, -215), (17, -237.7), (21, -237.7)],
    rf_y=[(0, -5), (4, -5), (10, -2), (17, -5), (21, -5)],
    rf_lift=[(0, 0), (4, 0), (5, 2), (7, 9), (10, 10), (14, 6), (16, 2), (17, 0), (21, 0)],
    rf_heel=[(0, 0), (2, 4), (3, 15), (4, 28), (5, 30), (8, 5), (13, 0), (21, 0)],
    # guard: hand targets in the chest's frame (given in rest-pose coordinates), plus small balance offsets
    lh_dx=[(0, 0), (4, -4), (9, -6), (14, -2), (21, 0)], lh_dz=[(0, 0), (4, 2), (9, 3), (14, -1), (21, 0)],
    rh_dx=[(0, 0), (5, 2), (10, 3), (15, 0), (21, 0)], rh_dz=[(0, 0), (5, -1), (12, -2), (21, 0)],
))

RIGHT_V1 = Mirror("Right", LEFT_V1)

class Turned(Design):
    """The Left hop turned onto the fore-aft axis (the owner, 2026-11-11: forward and back must be one jump like left
    and right, not several quick steps). Left's design is time-scaled onto this clip's own duration and its travel
    scaled to this clip's distance; this clip's motion data and annotations are kept as they are. The foot on the side
    of travel leads (Forward: the front, left foot; Back: the rear, right foot) and the other follows, each in one long
    swing, exactly as Left's lead and trail feet do. Left's sideways lean becomes a pitch toward the travel."""
    def __init__(self, name, src, sign):
        super().__init__(name, {})
        self.src, self.sign = src, sign                       # sign +1 forward, -1 back
        self.s = abs(self.motion[-1][2]) / abs(src.motion[-1][1])
        self.k = (src.nf - 1) / (self.nf - 1)                 # this frame -> Left frame
        self.lead, self.trail = ("lf", "rf") if sign > 0 else ("rf", "lf")
        self.lean = 1.0 if sign > 0 else 0.5                  # lean back less than forward
    def fl(self, f): return f * self.k
    def v(self, name, f):
        S, g = self.src, self.fl(f)
        if name == "hip_pitch":   return S.v("hip_pitch", g) + self.sign * self.lean * S.v("hip_roll", g)
        if name == "spine_pitch": return S.v("spine_pitch", g) + self.sign * self.lean * S.v("spine_roll", g)
        if name in ("hip_roll", "spine_roll"): return 0.0
        if name == "hip_yaw":     return S.v("hip_yaw", g)
        if name in ("lh_dy", "rh_dy"): return -self.sign * S.v(name[:3] + "dx", g)
        if name in ("lh_dz", "rh_dz"): return S.v(name, g)
        return 0.0
    def com_local(self, f):
        S, g = self.src, self.fl(f)
        a = -(S.root(g).x + S.v("com_off_x", g)) * self.s              # distance travelled along the dodge
        w = Vector((0, 0.5 + self.sign * a, 0))
        loc = w - self.root(f); loc.z = S.v("com_z", g)
        return loc
    def foot(self, pre, f):
        S, g = self.src, self.fl(f)
        if pre == self.lead:   x, y, lift, heel = S.foot("lf", g); a = -x - 14.0   # Left's lead foot
        else:                  x, y, lift, heel = S.foot("rf", g); a = -x + 14.0   # Left's trail foot
        sx, sy = (-14.0, 4.0) if pre == "lf" else (14.0, -5.0)                     # this foot's own stance
        return sx, sy + self.sign * a * self.s, lift * math.sqrt(self.s), heel

# Former designs, replaced 2026-11-11 by Turned (they read as several quick steps, not one jump):
# Forward: 409 units in 0.867 s is far more than one step can cover, so it is a lunge into a short run-out:
# anticipation dip with the body held back, push off the rear (right) foot, a long low lunge onto the left,
# two quick running steps with the trunk pitched forward, and a right-left catch-up into the stance.
_FY = 409.283
FORWARD_V0 = Design("Forward", dict(
    com_off_x=[(0, 0), (3, 2), (8, -3), (13, 3), (18, -3), (23, 1), (26, 0)],
    com_off_y=[(0, 0.5), (2, -9), (4, -13), (7, -6), (11, 3), (17, 8), (22, 6), (26, 0.5)],
    com_z=[(0, 64.5), (2, 60), (4, 61), (7, 57.5), (9, 59), (12, 57.5), (14, 59), (17, 57.5), (19, 59), (22, 58),
           (24, 61.5), (26, 64.5)],
    hip_pitch=[(0, -2), (3, -6), (7, -10), (14, -11), (20, -8), (24, -4), (26, -2)],
    hip_roll=[(0, 0), (8, 2), (13, -2), (18, 2), (23, -1), (26, 0)],
    hip_yaw=[(0, 0), (4, -4), (8, 5), (13, -5), (18, 5), (22, -3), (26, 0)],
    spine_pitch=[(0, -3), (4, -7), (14, -8), (22, -5), (26, -3)],
    lh_dy=[(0, 0), (5, 3), (9, -3), (13, 3), (18, -3), (22, 1), (26, 0)],
    rh_dy=[(0, 0), (5, -3), (9, 3), (13, -3), (18, 3), (22, -1), (26, 0)],
    **gait("lf", [(0, 2, -14, 4, 14), (7, 10, -12, 115, 25), (17, 20, -12, 347, 22), (24, 26, -14, _FY + 4, 0)],
           [6, 10, 5]),
    **gait("rf", [(0, 4, 14, -5, 28), (12, 15, 12, 236, 25), (22, 26, 14, _FY - 5, 0)], [10, 9]),
))

# Back: a hop-step backward - dip and lean in, push off the ball of the front (left) foot, low hop back onto the
# right foot, the left catches up, the right steps back once more to brake, the left adjusts into the stance.
BACK_V0 = Design("Back", dict(
    com_off_x=[(0, 0), (10, 2), (16, -2), (21, 1), (24, 0)],
    com_off_y=[(0, 0.5), (2, 10), (4, 12), (7, 4), (11, -6), (16, -10), (20, -6), (24, 0.5)],
    com_z=[(0, 64.5), (2, 59.5), (4, 61.5), (7, 63.5), (10, 58), (13, 57), (17, 60), (21, 63), (24, 64.5)],
    hip_pitch=[(0, -2), (2, -6), (5, 1), (10, 0), (15, -6), (19, -4), (24, -2)],
    hip_roll=[(0, 0), (9, 2), (15, -2), (21, 0.5), (24, 0)],
    hip_yaw=[(0, 0), (5, 3), (12, -3), (18, 2), (24, 0)],
    spine_pitch=[(0, -3), (2, -6), (6, -1), (15, -7), (24, -3)],
    lh_dy=[(0, 0), (4, 4), (10, 2), (16, -1), (24, 0)], rh_dy=[(0, 0), (4, 4), (10, 2), (16, -1), (24, 0)],
    lh_dz=[(0, 0), (4, 2), (12, 0), (24, 0)], rh_dz=[(0, 0), (4, 2), (12, 0), (24, 0)],
    **gait("lf", [(0, 3, -14, 4, 22), (15, 19, -12, -262, 8), (23, 24, -14, -296, 0)], [7, 3]),
    **gait("rf", [(0, 2, 14, -5, 8), (9, 12, 12, -172, 20), (19, 24, 14, -305, 0)], [7, 6]),
))

# v1 (prototype-v1, tag anim-prototype-v1): Forward/Back were LEFT_V1 turned onto the fore-aft axis.
FORWARD_V1 = Turned("Forward", LEFT_V1, +1)
BACK_V1 = Turned("Back", LEFT_V1, -1)
# ---- v2: step, bound, the other foot follows (the owner, 2026-11-11) -------------------------------------------
# "if you're dodging right, then your right foot moves to the right, and then your left follows it soon after your
# right touches down ... when I dodge forward, I kick off with my right foot, lift my left foot. Land with my left foot
# forward, and my right foot that jumped off catches up to the left and hits the floor second."
# A leg reaches only ~40 units from the body, so each clip is one bound: the lead foot lifts first, the push foot
# kicks off a moment later, the lead foot lands at its end stance, then the push foot swings through and lands beside
# it. Foot paths along the travel axis are given as explicit keys so each foot stays within reach of the body.
def _feet(g, axis, lead, push):
    """gait() for plants and lifts, then the travel-axis path of each foot replaced by explicit keys."""
    out = {}
    out.update(gait(lead[0], lead[1], lead[2])); out.update(gait(push[0], push[1], push[2]))
    out[lead[0] + "_" + axis] = lead[3]; out[push[0] + "_" + axis] = push[3]
    return out

# ---- v3 (the owner, 2026-11-12 18:04): "make sure that their feet never leave the ground ... Or if they do, make it a
# very, very low or small elevation ... lean into a jump in the direction you're jumping or dodging. And then on landing,
# or as you land, pull back a little in the opposite direction as the knee shoulders the blow of the landing."
# A heavy step, not a hop: the lead foot skims (at most 2 units up), the push foot SLIDES on the floor behind the body
# until the lead foot has landed and only then lifts 1.5 units to set down - so one foot is always on the floor. The
# body stays below the stance height the whole way (no bob), the trunk leans 20-30 degrees into the travel, and rocks
# back past upright as the lead knee takes the landing before it settles.
LEAD_SKIM, PUSH_SET = 2.0, 1.5
def grounded(K, lead, push, push_land, e, pre=()):
    """Lead foot's swing scaled to LEAD_SKIM; push foot on the floor (sliding) until 3 frames before it lands, a
    PUSH_SET lift to set it down. pre: lift keys of the push foot before its slide (a stance switch's shuffle)."""
    L = K[lead + "_lift"]; m = max(v for _, v in L) or 1.0
    K[lead + "_lift"] = [(f, v * LEAD_SKIM / m) for f, v in L]
    K[push + "_lift"] = list(pre) + [(max(pre[-1][0] + 1 if pre else 0, push_land - 3), 0.0),
                                    (push_land - 1.5, PUSH_SET), (push_land, 0.0), (e, 0.0)]
    if not pre: K[push + "_lift"].insert(0, (0, 0.0))
    return K

RIGHT = Design("Right", dict(
    com_off_x=[(0, 0), (2, -14), (3, -24), (5, -14), (9, 0), (12, 12), (14, 15), (15, 16), (17, 16), (19, 8), (21, 0)],
    com_off_y=[(0, 0.5), (21, 0.5)],
    # 2026-11-12 rework (the owner: "make the torso move in the direction of the dodge and make the step dodges lower
    # to the ground with more knee bending on arrival"): the whole step ~5 units lower, the landing compression deeper
    # (pelvis dips to ~51 on the lead foot's landing) before rising back to the stance; the trunk leans into the travel
    # through the push and flight and is upright again after the landing.
    com_z=[(0, 64.5), (2, 58), (3, 56), (5, 55.5), (8, 56), (11, 55.5), (13, 54.5), (15, 52.5), (17, 50.5), (19, 55.5), (21, 64.5)],
    hip_roll=[(0, 0), (2, 8), (4, 15), (8, 18), (12, 15), (14, 7), (15, 0), (16, -6), (17, -9), (19, -5), (21, 0)],   # + leans right
    hip_pitch=[(0, -2), (3, -6), (7, -4), (12, -3), (16, -6), (19, -4), (21, -2)],
    hip_yaw=[(0, 0), (3, 3), (9, -2), (15, 2), (21, 0)],
    spine_roll=[(0, 0), (3, 7), (6, 15), (10, 16), (13, 9), (15, -1), (17, -6), (19, -3), (21, 0)],
    spine_pitch=[(0, -3), (3, -7), (15, -6), (21, -3)],
    # knee_in 0..1 (the owner, 2026-11-12: "the knee you land on should point toward the body on landing"): turns that
    # leg's knee from slightly out (0) to in toward the centre line (1) through its landing and absorb
    rf_knee_in=[(0, 0), (12, 0), (14, 1), (19, 1), (21, 0)], lf_knee_in=[(0, 0), (17, 0), (19, 0.8), (21, 0)],
    lh_dx=[(0, 0), (4, -3), (10, 2), (16, 4), (21, 0)], lh_dz=[(0, 0), (5, 2), (13, -2), (21, 0)],
    rh_dx=[(0, 0), (4, -3), (10, 2), (16, 4), (21, 0)], rh_dz=[(0, 0), (5, 2), (13, -2), (21, 0)],
    **_feet(None, "x",
        ("rf", [(0, 2, 12, -16, 6), (15, 21, 263.2, -16, 0)], [14],
         [(0, 12), (2, 12), (5, 68), (9, 163), (12, 213), (14, 248), (15, 263.2), (21, 263.2)]),
        ("lf", [(0, 3, -12, 16, 30), (19, 21, 239.2, 16, 0)], [12],
         [(0, -12), (3, -12), (6, 47), (9, 102), (13, 182), (16, 224), (19, 239.2), (21, 239.2)])),
))
grounded(RIGHT.K, "rf", "lf", 19, 21)
LEFT = Mirror("Left", RIGHT)

_FY = 409.283
FORWARD = Design("Forward", dict(
    com_off_x=[(0, 0), (26, 0)],
    com_off_y=[(0, 0.5), (2, -8), (4, -16), (7, -6), (11, 5), (15, 14), (17, 22), (20, 24), (23, 10), (26, 0.5)],
    com_z=[(0, 64.5), (2, 59), (4, 56), (7, 55.5), (11, 56), (15, 55), (18, 53.5), (20, 52), (22, 50.5),
           (24, 56), (26, 64.5)],
    hip_pitch=[(0, -2), (3, -10), (6, -17), (11, -20), (17, -17), (19, -7), (20, 1), (21, 6), (23, 3), (26, -2)],
    hip_roll=[(0, 0), (4, -2), (10, 1), (17, 2), (21, -1), (26, 0)],
    hip_yaw=[(0, 0), (3, -3), (6, -6), (12, 2), (17, 5), (22, -2), (26, 0)],
    spine_pitch=[(0, -3), (4, -11), (11, -16), (17, -14), (19, -5), (21, 5), (23, 2), (26, -3)],
    lf_knee_in=[(0, 0), (17, 0), (19, 1), (24, 1), (26, 0)], rf_knee_in=[(0, 0), (21, 0), (23, 0.8), (25, 0.6), (26, 0)],
    lh_dy=[(0, 0), (6, 4), (14, -2), (20, 2), (26, 0)], rh_dy=[(0, 0), (6, -4), (14, 2), (20, -2), (26, 0)],
    **_feet(None, "y",
        ("lf", [(0, 2, -12, 16, 10), (20, 26, -12, _FY + 16, 0)], [14],
         [(0, 16), (2, 16), (5, 57), (9, 162), (13, 272), (17, 367), (20, _FY + 16), (26, _FY + 16)]),
        ("rf", [(0, 4, 12, -16, 30), (23, 26, 12, _FY - 16, 0)], [12],
         [(0, -16), (4, -16), (7, 50), (11, 155), (15, 255), (19, 340), (23, _FY - 16), (26, _FY - 16)])),
))

grounded(FORWARD.K, "lf", "rf", 23, 26)

BACK = Design("Back", dict(
    com_off_x=[(0, 0), (24, 0)],
    com_off_y=[(0, 0.5), (2, 10), (3, 20), (5, 10), (8, 0), (10, -8), (14, -18), (17, -24), (19, -14), (22, -4), (24, 0.5)],
    com_z=[(0, 64.5), (2, 58), (3, 56), (5, 55.5), (8, 56), (11, 55.5), (14, 54.5), (16, 53), (18, 51), (20, 52.5),
           (22, 57), (24, 64.5)],
    # + pitch leans back, into this clip's travel; forward again to absorb the landing, then the stance
    hip_pitch=[(0, -2), (3, -4), (6, 8), (10, 15), (14, 13), (16, 4), (17, -5), (19, -10), (21, -6), (24, -2)],
    hip_roll=[(0, 0), (5, 2), (12, -1), (18, 1), (24, 0)],
    hip_yaw=[(0, 0), (3, 3), (9, -3), (16, 2), (24, 0)],
    spine_pitch=[(0, -3), (3, -4), (7, 9), (11, 14), (15, 8), (17, -3), (19, -8), (21, -5), (24, -3)],
    rf_knee_in=[(0, 0), (14, 0), (16, 1), (21, 1), (24, 0)], lf_knee_in=[(0, 0), (19, 0), (21, 0.8), (23, 0.6), (24, 0)],
    lh_dy=[(0, 0), (4, 4), (10, 2), (16, -1), (24, 0)], rh_dy=[(0, 0), (4, 4), (10, 2), (16, -1), (24, 0)],
    **_feet(None, "y",
        ("rf", [(0, 1, 12, -16, 6), (17, 24, 12, -316.0, 0)], [12],
         [(0, -16), (1, -16), (4, -60), (8, -165), (12, -232), (14, -262), (15, -284), (17, -316.0), (24, -316.0)]),
        ("lf", [(0, 3, -12, 16, 28), (21, 24, -12, -284.0, 0)], [10],
         [(0, 16), (3, 16), (6, -60), (10, -140), (14, -210), (18, -262), (21, -284.0), (24, -284.0)])),
))

grounded(BACK.K, "rf", "lf", 21, 24)

class Roll(Design):
    """A simple tucked roll: crouch, dive, one full turn (end over end for Forward/Back, sideways for Left/Right),
    then rise into the combat stance. tuck 0..1 carries the feet from their floor plants to tucked points that turn
    with the body, and lets the head follow the body instead of staying level; solve_pose lifts the body wherever a
    joint would go through the floor. axis 'pitch' turns about the actor's X, 'roll' about Y; sign is the travel
    direction along that clip's axis (+ forward / right)."""
    roll = True
    def __init__(self, name, axis, sign, K):
        super().__init__(name, K)
        self.axis, self.sign = axis, sign
        self.T = self.root(self.nf - 1)
    def v(self, name, f):
        g = lambda n: mono(self.K[n], f) if n in self.K else 0.0
        turn = g("turn") * self.sign * (-1 if self.axis == "pitch" else 1)   # forward roll = pitch toward -
        if name == "hip_pitch": return g("lean") + (turn if self.axis == "pitch" else 0.0)
        if name == "hip_roll":  return turn if self.axis == "roll" else 0.0
        return g(name)
    def com_local(self, f):
        lag = self.v("lag", f) * self.sign
        off = Vector((lag, 0, 0)) if self.axis == "roll" else Vector((0, lag, 0))
        return Vector((0, 0.5, self.v("com_z", f))) + off
    def foot(self, pre, f):
        sx, sy = (-12.0, 16.0) if pre == "lf" else (12.0, -16.0)     # staggered stance, left foot forward
        if f <= self.nf / 2: return sx, sy, 0.0, 0.0                       # take-off plants
        return sx + self.T.x, sy + self.T.y, 0.0, 0.0                       # landing plants

def roll_keys(n, a, b, c, d):
    """Curves on the clip's own frames: a = take-off starts, b = tucked, c = untuck starts, d = on the feet."""
    e = n - 1
    return dict(
        tuck=[(0, 0), (a, 0), (b, 1), (c, 1), (d, 0), (e, 0)],
        turn=[(0, 0), (a + 1, 10), (b + 1, 100), ((b + c) / 2 + 1, 200), (c, 320), (d, 360), (e, 360)],
        lean=[(0, -2), (a, -18), (b, -25), (c, -22), (d, -10), (e, -2)],
        spine_pitch=[(0, -3), (a, -18), (b, -80), (c, -80), (d, -18), (e, -3)],
        com_z=[(0, 64.5), (a, 51), (b, 38), (c, 38), (d, 49), (e, 64.5)],
        lag=[(0, 0), (a, -6), (b + 1, 4), (d, 0), (e, 0)],
        # the owner, 2026-11-11: "your arms go in between your legs with your head as you dive forward so that your
        # back hits the ground and you keep rolling with your weapon drawn" - both hands (weapon in hand) reach down
        # between the knees while tucked; the head tucks (neck_tuck / head_tuck below, chin to chest)
        lh_dx=[(0, 0), (a, 2), (b, 5), (c, 5), ((c + d) / 2, 0), (e, 0)], rh_dx=[(0, 0), (a, -2), (b, -5), (c, -5), ((c + d) / 2, 0), (e, 0)],
        lh_dy=[(0, 0), (a, 4), (b, 12), (c, 12), ((c + d) / 2, 2), (d, 2), (e, 0)], rh_dy=[(0, 0), (a, 4), (b, 14), (c, 14), ((c + d) / 2, 2), (d, 2), (e, 0)],
        # coming out the hands are already up, higher than the guard, then settle (the owner, 2026-11-11)
        lh_dz=[(0, 0), (a, -8), (b, -24), (c, -24), ((c + d) / 2, 6), (d, 9), (e, 0)],
        rh_dz=[(0, 0), (a, -8), (b, -22), (c, -22), ((c + d) / 2, 6), (d, 9), (e, 0)],
        # head well tucked so the roll goes over the back - the head never touches the floor (the owner, 2026-11-11)
        neck_tuck=[(0, 0), (a, 15), (b, 80), (c, 80), (d, 6), (e, 0)],
        head_tuck=[(0, 0), (a, 12), (b, 60), (c, 60), (d, 4), (e, 0)],
    )
ROLL_LEFT = Roll("RollLeft", "roll", -1, roll_keys(22, 2, 6, 15, 18))
ROLL_RIGHT = Roll("RollRight", "roll", +1, roll_keys(22, 2, 6, 15, 18))
def forward_roll_keys():
    """The owner, 2026-11-11: "the roll dodges should not immediately go into a roll. It's more of diving forward with
    your arms outstretched, but going between your legs. And by the time you stand up, your feet are already where they
    should be." Crouch (0-3), dive forward with the arms reaching out ahead, body long, legs still pushing (3-8), the
    head tucks and the arms go down between the legs (8-11), roll over the back (11-18), unroll onto feet already
    planted in the end stance (18-22), stand (22-26). 27 frames (0.867 s, the clip's length)."""
    return dict(
        tuck=[(0, 0), (4, 0), (6, 0.4), (9, 0.85), (11, 1), (18, 1), (22, 0), (26, 0)],   # feet push off and leave early
        turn=[(0, 0), (3, 5), (8, 55), (11, 105), (14, 200), (18, 320), (21, 360), (26, 360)],
        lean=[(0, -2), (3, -15), (8, -10), (11, -15), (18, -20), (22, -10), (26, -2)],
        spine_pitch=[(0, -3), (3, -12), (8, -15), (11, -70), (18, -80), (22, -18), (26, -3)],   # long in the dive
        com_z=[(0, 64.5), (3, 52), (8, 44), (11, 36), (18, 36), (22, 49), (26, 64.5)],
        lag=[(0, 0), (3, -6), (8, 12), (12, 4), (22, 0), (26, 0)],
        # arms stretched out ahead in the dive, then down between the legs into the roll, then up high coming out
        lh_dx=[(0, 0), (3, 2), (8, 4), (11, 5), (18, 5), (20, 0), (26, 0)], rh_dx=[(0, 0), (3, -2), (8, -4), (11, -5), (18, -5), (20, 0), (26, 0)],
        lh_dy=[(0, 0), (3, 10), (8, 24), (11, 14), (18, 12), (20, 2), (22, 2), (26, 0)],
        rh_dy=[(0, 0), (3, 10), (8, 24), (11, 16), (18, 14), (20, 2), (22, 2), (26, 0)],
        lh_dz=[(0, 0), (3, -5), (8, -12), (11, -24), (18, -24), (20, 6), (22, 9), (26, 0)],
        rh_dz=[(0, 0), (3, -5), (8, -12), (11, -22), (18, -22), (20, 6), (22, 9), (26, 0)],
        neck_tuck=[(0, 0), (7, 5), (10, 45), (18, 45), (22, 6), (26, 0)],
        head_tuck=[(0, 0), (7, 4), (10, 35), (18, 35), (22, 4), (26, 0)],
    )
ROLL_FORWARD = Roll("RollForward", "pitch", +1, forward_roll_keys())
def back_roll_keys():
    """A gymnastics backward roll, from the coaching notes the owner sent (2026-11-11): squat and roll onto the bottom
    first with a rounded back; push through the heels, tuck the chin, bend the arms; hands by the ears, palms flat,
    pushing the floor away so the weight comes off the neck; feet point behind, not to the ceiling; land on the feet
    and stand. 25 frames (0.8 s, the clip's length)."""
    return dict(
        tuck=[(0, 0), (5, 0), (9, 1), (16, 1), (20, 0), (24, 0)],
        turn=[(0, 0), (6, 5), (9, 60), (12, 150), (15, 250), (18, 330), (20, 360), (24, 360)],
        lean=[(0, -2), (3, -15), (6, -20), (16, -20), (20, -12), (24, -2)],          # rounded back
        spine_pitch=[(0, -3), (3, -20), (7, -55), (16, -60), (20, -20), (24, -3)],
        com_z=[(0, 64.5), (3, 48), (6, 32), (9, 30), (16, 30), (20, 46), (24, 64.5)],  # squat, sit, roll, stand
        lag=[(0, 0), (4, 4), (9, -4), (20, 0), (24, 0)],
        # hands up by the ears, palms back, elbows bent - they meet the floor beside the head and push it away
        lh_dx=[(0, 0), (3, -2), (6, -4), (17, -4), (20, 0), (24, 0)], rh_dx=[(0, 0), (3, 2), (6, 4), (17, 4), (20, 0), (24, 0)],
        lh_dy=[(0, 0), (3, -8), (6, -16), (17, -16), (20, 2), (24, 0)], rh_dy=[(0, 0), (3, -7), (6, -14), (17, -14), (20, 2), (24, 0)],
        lh_dz=[(0, 0), (3, 10), (6, 21), (17, 21), (20, 9), (24, 0)], rh_dz=[(0, 0), (3, 11), (6, 23), (17, 23), (20, 9), (24, 0)],
        neck_tuck=[(0, 0), (4, 15), (8, 45), (16, 45), (20, 6), (24, 0)],          # chin tucked
        head_tuck=[(0, 0), (4, 10), (8, 35), (16, 35), (20, 4), (24, 0)],
    )
ROLL_BACK = Roll("RollBack", "pitch", -1, back_roll_keys())
TUCK = {"L": Vector((-7.0, -4.0, -24.0)), "R": Vector((7.0, -4.0, -24.0))}   # feet close together: knees do not splay (owner, 2026-11-11)   # ankle offset from the COM, body frame

DESIGNS = {"Left": LEFT, "Right": RIGHT, "Forward": FORWARD, "Back": BACK,
           "RollLeft": ROLL_LEFT, "RollRight": ROLL_RIGHT, "RollForward": ROLL_FORWARD, "RollBack": ROLL_BACK}
# Unarmed variants: the same motion with open hands and the unarmed guard, written to unarmed\<file>.hkx; they
# ship as the OAR submod "Simple Dodge\Unarmed" (both hands empty), so they replace the clips above only unarmed.
# ---- 8-way: the four diagonals (the owner, 2026-11-11: "we can start making the diagonal 8-way dodges") -----------
# Each diagonal is a side dodge laid onto a 45-degree axis: Forward-Left / Back-Left take LEFT's footwork (push off the
# right, land on the left first), Forward-Right / Back-Right take RIGHT's (push off the left, land on the right) - the
# push foot always lands second. Same timing as the side clip; travel scaled to the diagonal's distance; the side lean
# split into roll and pitch along the axis. Our own clips only (step-dodge replacer packs have no diagonals).
DIAG = {  # name: (source, unit axis (x, y), travel units)
    "ForwardLeft": ("Left", (-0.7071, 0.7071), 320.0), "ForwardRight": ("Right", (0.7071, 0.7071), 320.0),
    "BackLeft": ("Left", (-0.7071, -0.7071), 280.0), "BackRight": ("Right", (0.7071, -0.7071), 280.0),
}
for _n, (_src, (_ux, _uy), _dist) in DIAG.items():
    _S = SPEC[_src]; _tot = abs(_S["motion"][-1][1])
    _mo = [(t, _ux * abs(x) / _tot * _dist, _uy * abs(x) / _tot * _dist) for t, x, y in _S["motion"]]
    SPEC[_n] = dict(md=None, duration=_S["duration"], motion=_mo,
                    ann=[(round(t, 4), "animmotion %s %s 0" % (_g(round(x, 3)), _g(round(y, 3)))) for t, x, y in _mo])

class Diagonal(Design):
    def __init__(self, name, src, axis):
        super().__init__(name, {})
        self.src = src; self.u = Vector((axis[0], axis[1], 0.0))
        self.sgn = 1.0 if src.motion[-1][1] > 0 else -1.0      # +1 when the source travels to +x (Right)
        self.k = abs(self.motion[-1][1] ** 2 + self.motion[-1][2] ** 2) ** 0.5 / abs(src.motion[-1][1])
        self.foot_yaw = {"L": 0.0, "R": -45.0}                    # rear foot half-way between side and front/back
    def v(self, name, f):
        S = self.src
        lean = S.v("hip_roll", f) * self.sgn                      # + = leaning toward the travel
        slean = S.v("spine_roll", f) * self.sgn
        if name == "hip_roll":    return lean * self.u.x
        if name == "hip_pitch":   return S.v("hip_pitch", f) - lean * self.u.y
        if name == "spine_roll":  return slean * self.u.x
        if name == "spine_pitch": return S.v("spine_pitch", f) - slean * self.u.y
        if name == "hip_yaw":     return S.v("hip_yaw", f) * self.sgn * (1 if self.u.y >= 0 else -1) * 0.5
        return S.v(name, f)
    # 2026-11-12: laid onto the diagonal, the lead foot lands further from the hips than in the side clip (the stance's
    # own fore-aft offset adds to the travel), so the lead leg reached full stretch and landed straight. The body is
    # carried a little further along the axis and lower through the landing, so that leg arrives bent.
    LAND_LEAD = [(0, 0), (10, 0), (13, 5), (15, 6), (18, 3), (21, 0)]
    LAND_DZ = [(0, 0), (11, 0), (14, -3), (16, -2), (19, 0), (21, 0)]
    PUSH_EARLY = [(0, 0), (2, 0), (4, 9), (7, 6), (10, 0), (21, 0)]
    def com_local(self, f):
        S = self.src
        w = (S.com_local(f) + S.root(f)).x * self.sgn * self.k   # body travel along the dodge axis
        w += mono(self.LAND_LEAD, f)
        world = Vector((0.0, 0.5, 0.0)) + self.u * w
        loc = world - self.root(f); loc.z = S.com_local(f).z + mono(self.LAND_DZ, f)
        return loc
    def foot(self, pre, f):
        x, y, lift, heel = self.src.foot(pre, f)
        x0 = self.src.foot(pre, 0)[0]
        a = (x - x0) * self.sgn * self.k
        # v3: the push foot (Right's left, Left's right) starts its floor slide a little early on the diagonal, where
        # the body leaves it faster than in the side clip - left planted it was stretched past reach at frame 4 and
        # its toe rose ~5 units
        if pre == ("lf" if self.sgn > 0 else "rf"):
            a += mono(self.PUSH_EARLY, f)
        sx, sy = (-12.0, 16.0) if pre == "lf" else (12.0, -16.0)
        p = Vector((sx, sy, 0.0)) + self.u * a
        return p.x, p.y, lift, heel

for _n, (_src, _axis, _dist) in DIAG.items():
    DESIGNS[_n] = Diagonal(_n, DESIGNS[_src], _axis)

# Forward-Right and Back-Left switch stance (the owner, 2026-11-11): "the forward right and backward left dodges have to
# turn the whole character's body to position the leg that they're pushing off with forward ... they have to bring
# their right foot forward and their left foot back and jump, and that should turn their whole body as they do that."
# The push foot steps across to the other side of the stance while the whole body turns (body_yaw, hips and chest
# together, head kept to the front), the lead foot travels all the way to its landing in one swing, then the push foot
# swings through and lands second - ending in the normal stance (left foot forward), the body turned back. The switch
# comes before the travel, so these two clips are 5 frames longer and their motion starts 0.1667 s later.
SWITCH_DELAY = 5
class SwitchDiagonal(Design):
    def __init__(self, name, axis, dist, K):
        super().__init__(name, K)
        self.u = Vector((axis[0], axis[1], 0.0))
    def com_local(self, f):
        lag = self.v("lag", f)
        return Vector((0.0, 0.5, self.v("com_z", f))) + self.u * lag

def _switch_spec(name, src):
    S = SPEC[src]; tot = abs(S["motion"][-1][1]); _src_, (ux, uy), dist = DIAG[name]
    dt = SWITCH_DELAY / FPS
    mo = [(0.0, 0.0, 0.0), (dt, 0.0, 0.0)] + [(round(t + dt, 5), ux * abs(x) / tot * dist, uy * abs(x) / tot * dist)
                                               for t, x, y in S["motion"] if t > 0]
    SPEC[name] = dict(md=None, duration=round(S["duration"] + dt, 6), motion=mo,
                      ann=[(round(t, 4), "animmotion %s %s 0" % (_g(round(x, 3)), _g(round(y, 3)))) for t, x, y in mo])

def _switch_keys(name):
    _src, (ux, uy), dist = DIAG[name]; Ex, Ey = ux * dist, uy * dist; e = 26
    fwd = uy > 0                                   # Forward-Right: lead right, push left; Back-Left: lead left, push right
    lead, push = ("rf", "lf") if fwd else ("lf", "rf")
    st = {"lf": (-12.0, 16.0), "rf": (12.0, -16.0)}                 # normal stance (left foot forward)
    sw = {"lf": (-12.0, -16.0), "rf": (12.0, 16.0)}                 # switched stance
    K = dict(
        body_yaw=[(0, 0), (3, 25), (6, 50), (18, 50), (23, 25), (e, 0)],     # whole body turns to the switched side
        com_z=[(0, 64.5), (2, 60), (5, 56), (8, 55.5), (13, 56), (18, 54.5), (21, 52), (23, 50.5), (25, 56), (e, 64.5)],
        lag=[(0, 0), (4, -4), (8, 0), (16, 8), (21, 6), (e, 0)],
        hip_roll=[(0, 0), (6, 10 * ux / abs(ux)), (14, 12 * ux / abs(ux)), (19, 2 * ux / abs(ux)), (21, -6 * ux / abs(ux)),
                  (23, -3 * ux / abs(ux)), (e, 0)],
        spine_roll=[(0, 0), (6, 8 * ux / abs(ux)), (16, 8 * ux / abs(ux)), (21, -4 * ux / abs(ux)), (e, 0)],
        hip_pitch=[(0, -2), (6, -12 if fwd else 15), (14, -12 if fwd else 17), (19, -4 if fwd else 2), (21, 7 if fwd else -6),
                   (23, 2 if fwd else -3), (e, -2)],
        spine_pitch=[(0, -3), (6, -12 if fwd else 13), (16, -10 if fwd else 15), (21, 5 if fwd else -5), (e, -3)],
    )
    K[("rf" if fwd else "lf") + "_knee_in"] = [(0, 0), (19, 0), (21, 1), (24, 1), (e, 0)]      # lead foot lands at 21
    K[("lf" if fwd else "rf") + "_knee_in"] = [(0, 0), (23, 0), (25, 0.8), (e, 0.3)]           # push foot at 25
    K.update(gait(lead, [(0, 3, st[lead][0], st[lead][1], 10), (21, e, st[lead][0] + Ex, st[lead][1] + Ey, 0)], [14]))
    if not fwd:
        # Back-Left, amended (the owner, 2026-11-11): "just bring the left foot back behind the character. And jump
        # with the right before the left foot lands" - no switch step: the right foot stays where it stands and pushes
        sw = dict(st)
        K.update(gait(push, [(0, 6, st[push][0], st[push][1], 30), (25, e, st[push][0] + Ex, st[push][1] + Ey, 0)], [12]))
    else:
        K.update(gait(push, [(0, 0, st[push][0], st[push][1], 8), (3, 6, sw[push][0], sw[push][1], 30),
                             (25, e, st[push][0] + Ex, st[push][1] + Ey, 0)], [5, 12]))
    # keep both feet within reach of the body: their travel follows the root (this clip's own motion data), the push
    # foot trailing behind it and passing under the body, the lead foot a little ahead of it until it lands
    mo = SPEC[name]["motion"]
    def root(fr):
        t = fr / FPS
        for (t0, x0, y0), (t1, x1, y1) in zip(mo, mo[1:]):
            if t <= t1:
                k = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
                return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
        return mo[-1][1], mo[-1][2]
    def path(pre, base, keys, start, end_fr):
        xs, ys = [(0, st[pre][0])], [(0, st[pre][1])]
        xs += [(start[0], start[1])]; ys += [(start[0], start[2])]
        for fr, off in keys:
            rx, ry = root(fr)
            xs.append((fr, base[0] + rx + ux * off)); ys.append((fr, base[1] + ry + uy * off))
        xs += [(end_fr, st[pre][0] + Ex), (e, st[pre][0] + Ex)]; ys += [(end_fr, st[pre][1] + Ey), (e, st[pre][1] + Ey)]
        K[pre + "_x"], K[pre + "_y"] = xs, ys
    path(push, st[push], [(9, -38), (12, -28), (15, -18), (18, -8), (21, -3)], (6, sw[push][0], sw[push][1]), 25)
    path(lead, st[lead], [(7, 26), (11, 36), (15, 34), (18, 20)], (3, st[lead][0], st[lead][1]), 21)
    # v3 grounding: the lead skims, the push foot slides until it sets down at 25 (Forward-Right keeps its 1.5-unit
    # stance-switch shuffle at frames 0-3, while the lead foot is still planted)
    grounded(K, lead, push, 25, e, pre=[(0, 0.0), (1.5, PUSH_SET), (3, 0.0)] if fwd else ())
    # foot turn per frame: the rear foot is turned out; the push foot becomes the rear foot while switched
    out = {"lf": 45.0, "rf": -45.0}
    K[lead + "_yaw"] = [(0, 0 if lead == "lf" else out["rf"]), (21, 0 if lead == "lf" else out["rf"]), (e, 0 if lead == "lf" else out["rf"])]
    K[push + "_yaw"] = [(0, 0 if push == "lf" else out["rf"]), (3, out[push]), (6, out[push]), (16, out[push] * 0.3),
                        (25, 0 if push == "lf" else out["rf"]), (e, 0 if push == "lf" else out["rf"])]
    return K

for _n in ("ForwardRight", "BackLeft"):
    _switch_spec(_n, DIAG[_n][0])
    DESIGNS[_n] = SwitchDiagonal(_n, DIAG[_n][1], DIAG[_n][2], _switch_keys(_n))

# The owner, 2026-11-11: "the side to side dodges should have front facing feet only the front and back would have the
# perpendicular feet" - left/right clips (step and roll) keep both feet pointing forward.
for _d in (LEFT, RIGHT, ROLL_LEFT, ROLL_RIGHT):
    _d.foot_yaw = {"L": 0.0, "R": 0.0}
import copy
os.makedirs(os.path.join(OUT, "unarmed"), exist_ok=True)
for _k in list(DESIGNS):
    _u = copy.copy(DESIGNS[_k]); _u.unarmed = True
    _u.name = _k + "Unarmed"; _u.file = os.path.join("unarmed", DESIGNS[_k].file)
    DESIGNS[_u.name] = _u

# ---- weapon grips (the owner, 2026-11-12: "now we need to add the weapon type anims for holding the weapons while
# dodging") -----------------------------------------------------------------------------------------------------------
# Each held-weapon type gets the eight step dodges with the arms, hands and weapon nodes of that type's VANILLA combat
# idle (frame 0 of the game's own idle, read from Skyrim - Animations.bsa), held through the whole step. Every bone
# from the clavicles out takes the idle's parent-local pose, so the arms ride the reworked spine lean; legs, pelvis and
# spine are the step's own. One idle per side: a set that mixes (one-handed + shield) takes each arm from its own idle,
# and the third value is the share of the second idle on that side (the shield carried half-raised, between the 1hm
# idle and the block idle). The idles are the game's, so they are read from the unpacked archive
# (SIMPLEDODGE_VANILLA_ANIMS, default ../_work/vanilla-anims/meshes/actors/character/animations); never shipped.
VANILLA_ANIMS = os.environ.get("SIMPLEDODGE_VANILLA_ANIMS", os.path.join(os.path.dirname(HERE), "_work", "vanilla-anims",
                               "meshes", "actors", "character", "animations"))
GRIPS = {   # set folder: {side: (idle, second idle or None, share of the second)}
    "OneHanded":          {"R": ("1hm_idle", None, 0.0), "L": ("1hm_idle", None, 0.0)},
    "OneHandedShield":    {"R": ("1hm_idle", None, 0.0), "L": ("1hm_idle", "shd_blockidle", 0.5)},
    "DualWield":          {"R": ("dw1hm1hmidle", None, 0.0), "L": ("dw1hm1hmidle", None, 0.0)},
    "Greatsword":         {"R": ("2hm_idle", None, 0.0), "L": ("2hm_idle", None, 0.0)},
    "BattleaxeWarhammer": {"R": ("2hw_idle", None, 0.0), "L": ("2hw_idle", None, 0.0)},
    "Bow":                {"R": ("bow_idledrawn", None, 0.0), "L": ("bow_idledrawn", None, 0.0)},
    "Crossbow":           {"R": ("dlc01/crossbow_idledrawn", None, 0.0), "L": ("dlc01/crossbow_idledrawn", None, 0.0)},
    "Staff":              {"R": ("staffright_idle", None, 0.0), "L": ("staffright_idle", None, 0.0)},
    "MagicRight":         {"R": ("mrh_idle", None, 0.0), "L": ("mrh_idle", None, 0.0)},
    "MagicLeft":          {"R": ("mlh_idle", None, 0.0), "L": ("mlh_idle", None, 0.0)},
    "MagicBoth":          {"R": ("dualmagic_idle", None, 0.0), "L": ("dualmagic_idle", None, 0.0)},
}
STEP_DIRS = ["Left", "Right", "Forward", "Back", "ForwardLeft", "ForwardRight", "BackLeft", "BackRight"]

def _side_bones():
    out = {"L": set(), "R": set()}
    for side in "LR":
        root = IDX[f"NPC {side} Clavicle [{side}Clv]"]
        for i in range(len(BN)):
            j = i
            while j >= 0 and j != root: j = PAR[j]
            if j == root: out[side].add(i)
    return out

_IDLE_CACHE = {}
def idle_locals(name):
    """Frame-0 parent-local (translation, rotation) per bone index of a vanilla idle (the bones it has tracks for)."""
    if name in _IDLE_CACHE: return _IDLE_CACHE[name]
    a = AS.load_skyrim_animation(os.path.join(VANILLA_ANIMS, *name.split("/")) + ".hkx")
    out = {}
    # an empty binding array means track i drives bone i (the game's own clips are written that way)
    binding = list(a.track_to_bone_indices) or list(range(len(a.tracks)))
    for tr, bi in enumerate(binding):
        if bi < 0 or tr >= len(a.tracks): continue
        t_, r_ = a.tracks[tr].translations[0], a.tracks[tr].rotations[0]
        out[bi] = (Vector(t_), Quaternion((r_[3], r_[0], r_[1], r_[2])))
    _IDLE_CACHE[name] = out
    return out

def grip_locals(spec):
    """bone index -> local 4x4 for every bone from the clavicles out, per side, from that side's idle(s)."""
    sides = _side_bones(); res = {}
    for side, (a, b, w) in spec.items():
        A = idle_locals(a); B = idle_locals(b) if b else None
        for i in sides[side]:
            if i not in A: continue
            t_, q = A[i]
            if B and i in B:
                t_ = t_.lerp(B[i][0], w); q = q.slerp(B[i][1], w)
            res[i] = Matrix.Translation(t_) @ q.to_matrix().to_4x4()
    return res

# ---- our own grips for the Animated Armoury / Heavy Armory weapon types (the owner, 2026-11-12) -----------------------
# Authored here from LOOKING at each type's idle (render_reference.py), not taken from that mod's animation data: a pole
# grip is the weapon's direction and the right hand's grip point in the chest's rest frame, and where the left hand
# holds the shaft (spread units along the pole from the right hand) or, for one-handed blades, an explicit left wrist
# point. The arms reach those points with the same two-bone IK as the guard; the Weapon node keeps the hand's position
# and turns its +Y (every weapon mesh's long axis, measured from the nifs) along the pole, rolled by roll degrees.
POLES = {
    # head up, haft nearly upright in front, right hand at the chest, left hand lower on the haft
    "Halberd":  dict(grip=(5.0, 24.0, 96.0), dir=(0.10, 0.25, 1.0), spread=-24.0, roll=0.0),
    # held low at the right hip, point forward and up across the body, left hand forward on the shaft
    "Pike":     dict(grip=(15.0, 14.0, 90.0), dir=(-0.15, 0.85, 0.45), spread=6.0, roll=0.0),
    # across the body, rising to the left, hands about shoulder-width apart
    "QtrStaff": dict(grip=(16.0, 18.0, 84.0), dir=(-0.85, 0.15, 0.50), spread=44.0, roll=0.0),
    # blade forward at chest height, arm out; the left hand back at the hip
    "Rapier":   dict(grip=(14.0, 34.0, 96.0), dir=(0.0, 1.0, 0.15), left=(-16.0, -6.0, 82.0), roll=90.0),
}
WEAPON_TYPE_GRIPS = {   # sets riding a vanilla idle (the game's own data)
    "Katana": {"R": ("2hm_idle", None, 0.0), "L": ("2hm_idle", None, 0.0)},     # two-handed, as the greatsword
    "Claws":  {"R": ("h2h_idle", None, 0.0), "L": ("h2h_idle", None, 0.0)},     # fists up, claws on them
}

def pole_frame(pg, Gch, G0ch):
    """World rotation of the Weapon node: +Y along the pole, +X rolled about it."""
    Rc = Gch.to_3x3() @ G0ch.to_3x3().inverted()
    y = (Rc @ Vector(pg["dir"])).normalized()
    up = (Rc @ Vector((0, 0, 1)))
    x = y.cross(up)
    if x.length < 1e-4: x = y.cross(Rc @ Vector((0, 1, 0)))
    x.normalize()
    x = (Matrix.Rotation(radians(pg.get("roll", 0.0)), 3, y) @ x).normalized()
    z = x.cross(y).normalized()
    return Matrix((x, y, z)).transposed()

def pole_wrist_target(pg, side, Gch, G0ch):
    """Wrist target (world) that puts that hand's palm node on the grip point / the shaft."""
    Rc = Gch.to_3x3() @ G0ch.to_3x3().inverted()
    grip = Gch @ (G0ch.inverted() @ Vector(pg["grip"]))
    d = (Rc @ Vector(pg["dir"])).normalized()
    if side == "R":
        return grip + Rc @ (P0("NPC R Hand [RHnd]") - P0("Weapon"))
    if "left" in pg:
        return Gch @ (G0ch.inverted() @ Vector(pg["left"]))
    return grip + d * pg["spread"] + Rc @ (P0("NPC L Hand [LHnd]") - P0("Shield"))

GRIPS.update(WEAPON_TYPE_GRIPS)
for _set, _pg in POLES.items():
    os.makedirs(os.path.join(OUT, "weapons", _set), exist_ok=True)
    for _k in STEP_DIRS:
        _w = copy.copy(DESIGNS[_k]); _w.grip_set = _set; _w.pole = _pg
        _w.name = _k + _set; _w.file = os.path.join("weapons", _set, DESIGNS[_k].file)
        DESIGNS[_w.name] = _w
# BEFORE for the new types: what each gets today - its vanilla-type set (pike: greatsword; halberd and quarterstaff:
# battleaxe; rapier and katana: one-handed; claws: dual wield), with the new type's weapon in hand
ARMOURY_TODAY = {"Halberd": "BattleaxeWarhammer", "Pike": "Greatsword", "QtrStaff": "BattleaxeWarhammer",
                 "Rapier": "OneHanded", "Katana": "OneHanded", "Claws": "DualWield"}
for _new, _old in ARMOURY_TODAY.items():
    for _k in STEP_DIRS:
        _b = copy.copy(DESIGNS[_k]); _b.grip_set = _old; _b.grip_spec = GRIPS[_old]; _b.weapon_show = _new
        _b.name = _k + _new + "Before"; _b.file = os.path.join("weapons", "_before", _new, DESIGNS[_k].file)
        os.makedirs(os.path.join(OUT, "weapons", "_before", _new), exist_ok=True)
        DESIGNS[_b.name] = _b

os.makedirs(os.path.join(OUT, "weapons"), exist_ok=True)
for _set in [s for s in GRIPS if s not in WEAPON_TYPE_GRIPS] + ["Dagger", "Warhammer"]:       # BEFORE: today's open-guard step, the same weapons in hand
    for _k in STEP_DIRS:
        _b = copy.copy(DESIGNS[_k]); _b.weapon_show = _set
        _b.name = _k + _set + "Before"; _b.file = os.path.join("weapons", "_before", _set, DESIGNS[_k].file)
        os.makedirs(os.path.join(OUT, "weapons", "_before", _set), exist_ok=True)
        DESIGNS[_b.name] = _b
for _set, _src in (("Dagger", "OneHanded"), ("Warhammer", "BattleaxeWarhammer")):   # same grip, other weapon mesh
    for _k in STEP_DIRS:
        _r = copy.copy(DESIGNS[_k]); _r.grip_set = _src; _r.grip_spec = GRIPS[_src]; _r.weapon_show = _set
        _r.name = _k + _set; _r.file = os.path.join("weapons", "_review", _set, DESIGNS[_k].file)
        os.makedirs(os.path.join(OUT, "weapons", "_review", _set), exist_ok=True)
        DESIGNS[_r.name] = _r
for _set, _spec in GRIPS.items():
    os.makedirs(os.path.join(OUT, "weapons", _set), exist_ok=True)
    for _k in STEP_DIRS:
        _w = copy.copy(DESIGNS[_k]); _w.grip_set = _set; _w.grip_spec = _spec
        _w.name = _k + _set; _w.file = os.path.join("weapons", _set, DESIGNS[_k].file)
        DESIGNS[_w.name] = _w

def ik2(s, t, l1, l2, pole):
    """Two-bone IK: joint position for root s, target t (clamped to reach), bending toward pole."""
    v = t - s; dist = v.length; d = v.normalized()
    dist_c = min(max(dist, abs(l1 - l2) + 1e-3), l1 + l2 - 1e-3)
    t = s + d * dist_c
    cos_a = (l1 * l1 + dist_c * dist_c - l2 * l2) / (2 * l1 * dist_c)
    a = math.acos(max(-1, min(1, cos_a)))
    p = (pole - d * pole.dot(d)).normalized()
    return s + (d * math.cos(a) + p * math.sin(a)) * l1, t, dist / (l1 + l2)

def frame_of(a, n):
    a = a.normalized(); n = (n - a * n.dot(a)).normalized(); c = a.cross(n)
    return Matrix((a, n, c)).transposed()

def chain_rot(a0, b0, a1, b1):
    """World rotation taking the rest chain plane (a0 = bone dir, b0 = next bone dir) onto the posed one."""
    n0 = a0.cross(b0); n1 = a1.cross(b1)
    if n0.length < 1e-4 or n1.length < 1e-4:
        return a0.rotation_difference(a1).to_matrix()
    return frame_of(a1, n1) @ frame_of(a0, n0).transposed()

FINGERS = {}
def finger_setup():
    for side in "LR":
        H = P0(f"NPC {side} Hand [{side}Hnd]")
        I = P0(f"NPC {side} Finger10 [{side}F10]"); Pk = P0(f"NPC {side} Finger40 [{side}F40]")
        n = (I - H).cross(Pk - H).normalized()
        if (n.x > 0) != (side == "L"):    # palm faces the thigh in the rest A-pose: +X for the left hand
            n = -n
        for fi in range(5):
            names = [f"NPC {side} Finger{fi}{j} [{side}F{fi}{j}]" for j in range(3)]
            pts = [P0(x) for x in names]
            dirs = [(pts[1] - pts[0]), (pts[2] - pts[1]), (pts[2] - pts[1])]
            curl = (18, 28, 20) if fi == 0 else (55, 80, 50)
            # unarmed: open hands, fingers extended with only a slight natural bend (the owner, 2026-11-11)
            curl_open = (0, -5, -5) if fi == 0 else (-12, -22, -12)    # past the rest pose, which is half curled
            for j, nm in enumerate(names):
                dd = dirs[j].normalized(); ax = dd.cross(n).normalized()
                FINGERS[IDX[nm]] = Rax(ax, curl[j])
                FINGERS_OPEN[IDX[nm]] = Rax(ax, curl_open[j])
FINGERS_OPEN = {}
finger_setup()
# Unarmed guard (the owner, 2026-11-11): "the right hand to be closer to the body and the left to be slightly
# outstretched" - right hand drawn in near the chest, left reaching forward, both open.
# Amended the same day: "both hands raised but with the left in front of the right and both should have a 90 degree
# angle bend at the elbow" - each hand sits at 0.707 of its arm's length from the shoulder (a right angle at the
# elbow when upper arm and forearm are equal), the left pointing forward, the right turned in across the chest
# so it rests behind the left (the 25-degree stance turn carries the right shoulder back as well).
def _unarmed_guard(side, d):
    s0 = P0(f"NPC {side} UpperArm [{side}Uar]"); e0 = P0(f"NPC {side} Forearm [{side}Lar]"); w0 = P0(f"NPC {side} Hand [{side}Hnd]")
    l1, l2 = (e0 - s0).length, (w0 - e0).length
    return s0 + Vector(d).normalized() * math.sqrt(l1 * l1 + l2 * l2)
# Amended again: "both hands should be at cheek level, but the left arm should be out further than the right. So keep
# the left arm where it's at, so it maintains its angle, but raise it up to cheek height and pull the right arm back
# closer to the face." Left: same reach (right angle at the elbow), its direction tipped up until the hand is at cheek
# height. Right: a hand's width in front of the right cheek, elbow folded tighter.
_HEAD = P0("NPC Head [Head]"); CHEEK_Z = _HEAD.z + 3.0
def _left_at_cheek():
    s0 = P0("NPC L UpperArm [LUar]"); e0 = P0("NPC L Forearm [LLar]"); w0 = P0("NPC L Hand [LHnd]")
    L = math.sqrt((e0 - s0).length ** 2 + (w0 - e0).length ** 2)
    dz = max(-L, min(L, CHEEK_Z - s0.z)); hz = math.sqrt(max(0.0, L * L - dz * dz))
    h = Vector((0.04, 0.96, 0.0)).normalized() * hz
    return s0 + Vector((h.x, h.y, dz))
# Given in the chest's rest frame, chosen so that after the 25-degree stance turn the left hand sits in front of the
# left cheek, further out (world about x -8, y +22), and the right hand beside the right cheek (world about x +10, y +6).
CHEEK_Z = _HEAD.z - 1.0     # the WRIST, so the palm sits at cheek height
LH_GUARD_UNARMED = Vector((-16.6, 16.6, CHEEK_Z))
RH_GUARD_UNARMED = Vector((6.5, 9.7, CHEEK_Z))

# joints that must stay above the floor in a roll, with the clearance each needs (body thickness around the joint)
FOOT_YAW = {"L": 0.0, "R": -80.0}   # stance foot turn about Z, degrees (- turns the toes to the right)
STANCE_YAW = -25.0     # hips and shoulders (right chest side pulled back) together, degrees about Z
def head_crown(G):
    """The top of the skull: 14 units up the head from the head joint (rest-pose up), carried by the head's rotation."""
    i = IDX["NPC Head [Head]"]
    return G[i].translation + (G[i].to_3x3() @ B0[i].transposed()) @ Vector((0.0, 2.0, 14.0))
CROWN_CLEAR = 7.0
# head joint (base of the skull) and neck joint (base of the neck, top of the back): the back of the neck may touch
CLEAR = (("Head", 10.0), ("Neck", 6.0), ("Spine", 8.0), ("Pelvis", 8.0), ("Clavicle", 7.0), ("UpperArm", 6.0),
         ("Forearm", 4.5), ("Hand", 3.5), ("Thigh", 7.0), ("Calf", 5.0))
def solve_pose(D, f):
    """World (root-local) 4x4 for every bone at frame f (0..NF-1). A roll is solved twice: the second time with the
    body raised by however far the first pass put a joint through the floor."""
    G, reach, feet = _solve_pose(D, f)
    if not D.roll: return G, reach, feet
    pen = 0.0
    hi = IDX["NPC Head [Head]"]                  # the crown of the head must stay off the floor too (owner, 2026-11-11)
    pen = max(pen, CROWN_CLEAR - head_crown(G).z)
    for i, n in enumerate(BN):
        if not n.startswith("NPC ") or "Root" in n: continue
        for key, c in CLEAR:
            if key in n: pen = max(pen, c - G[i].translation.z); break
    if pen <= 0: return G, reach, feet
    return _solve_pose(D, f, pen)

def _solve_pose(D, f, dz=0.0):
    RO = D.root(f)
    G = [None] * len(BN)
    delta = {}                                   # bone -> extra rotation in rest-world axes
    over = {}                                    # bone -> forced global rotation (3x3)
    com = IDX["NPC COM [COM ]"]
    com_pos = D.com_local(f)                                                 # root-local
    com_pos.z += dz
    w = D.v("tuck", f) if D.roll else 0.0
    # staggered stance (left foot forward): hips and shoulders turn together so the right shoulder sits back over the
    # right leg (the owner, 2026-11-11: "the hips and shoulder should match"); the head is held facing forward. The
    # turn fades out while a roll is tucked. The spine counters only the clip's own hip_yaw, not this stance turn.
    y0 = STANCE_YAW * (1 - w) + D.v("body_yaw", f)     # body_yaw: a whole-body turn some clips key (stance switch)
    Rhip = Rax('Z', D.v("hip_yaw", f) + y0) @ Rax('Y', D.v("hip_roll", f)) @ Rax('X', D.v("hip_pitch", f))
    sr, sp, sy = D.v("spine_roll", f) / 3, D.v("spine_pitch", f) / 3, -0.8 * D.v("hip_yaw", f) / 3
    for nm in ("NPC Spine [Spn0]", "NPC Spine1 [Spn1]", "NPC Spine2 [Spn2]"):
        delta[IDX[nm]] = Rax('Z', sy) @ Rax('Y', sr) @ Rax('X', sp)
    unarmed = getattr(D, "unarmed", False)
    for i, R in (FINGERS_OPEN if unarmed else FINGERS).items(): delta[i] = R
    feet = {}
    yaws = {}
    for side, pre in (("L", "lf"), ("R", "rf")):
        A = P0(f"NPC {side} Foot [{side}ft ]"); T = P0(f"NPC {side} Toe0 [{side}Toe]")
        fx_, fy_, lift, p = D.foot(pre, f)
        # foot turn (the owner, 2026-11-11): front (left) toes point where you face, the support (right) foot
        # perpendicular; eased toward straight while the foot is in the air, and the knee follows the foot
        if (pre + "_yaw") in D.K:   # a per-frame foot turn the clip keys itself
            Ry = Rax('Z', D.v(pre + "_yaw", f))
        else:
            Ry = Rax('Z', getattr(D, "foot_yaw", FOOT_YAW)[side] * (1 - 0.6 * min(1.0, lift / 6.0)))
        yaws[side] = Ry
        TA = Ry @ (T - A)
        fwd = Vector((TA.x, TA.y, 0)).normalized(); lat = fwd.cross(Vector((0, 0, 1)))
        heel_pt = A + Vector((0, 0, -A.z)) - fwd * 3.0           # back of the heel on the floor
        anchor = Vector((fx_ - RO.x, fy_ - RO.y, A.z))                     # flat-foot ankle position, root-local
        Rf = Rax(lat, -p) @ Ry
        if p >= 0:   pivot = anchor + TA                                   # ball of the foot
        else:        pivot = anchor + (heel_pt - A)
        ankle = pivot + Rf @ (anchor - pivot) + Vector((0, 0, lift))
        if w > 0:                                   # roll: the foot goes to its tucked point, turning with the body
            ankle = ankle.lerp(com_pos + Rhip @ TUCK[side], w)
            Rt_ = (Rhip @ Rax(lat, -35)).to_quaternion()
            Rf = Rf.to_quaternion().slerp(Rt_, w).to_matrix()
        feet[side] = (ankle, Rf, lift <= 0.05 and p >= 0 and w <= 0.02)
    reach = {}
    for i in range(len(BN)):
        par = PAR[i]; name = BN[i]
        if i == com:
            G[i] = Matrix.Translation(com_pos) @ (Rhip @ B0[i]).to_4x4(); continue
        base = (G[par] @ L0[i]) if par >= 0 else L0[i].copy()
        if i in delta:
            base = base @ (B0[i].transposed() @ delta[i] @ B0[i]).to_4x4()
        G[i] = base
        grip = getattr(D, "grip_spec", None)
        if grip is not None:
            GL = D.__dict__.get("_grip_L")
            if GL is None:
                GL = D._grip_L = grip_locals(grip)
            if i in GL:                       # arms, hands, weapon nodes: the weapon type's idle, riding the spine
                G[i] = G[par] @ GL[i]
                continue
        # legs
        for side in "LR":
            th, ca, fo, to = (IDX[f"NPC {side} Thigh [{side}Thg]"], IDX[f"NPC {side} Calf [{side}Clf]"],
                              IDX[f"NPC {side} Foot [{side}ft ]"], IDX[f"NPC {side} Toe0 [{side}Toe]"])
            if i == th:
                ankle, Rf, grounded = feet[side]
                s = G[i].translation
                h0, k0, a0 = P0(BN[th]), P0(BN[ca]), P0(BN[fo])
                l1, l2 = (k0 - h0).length, (a0 - k0).length
                # knee_in (2026-11-12): 0 = knee a touch outward (as before), 1 = in toward the centre line
                # The landing knee aims in from the HIPS' forward, not the foot's: a turned-out rear foot (FOOT_YAW)
                # would otherwise carry the knee out with it.
                kin = 0.0 if D.roll else max(0.0, min(1.0, D.v(("rf" if side == "R" else "lf") + "_knee_in", f)))
                sgn = 1.0 if side == "R" else -1.0
                pole_out = (yaws[side] @ Vector((sgn * 0.25, 1, 0))).normalized()
                pole_in = (Rax('Z', D.v("hip_yaw", f) + y0) @ Vector((-sgn * 0.55, 1, 0))).normalized()
                pole = pole_out.lerp(pole_in, kin)
                if D.roll:            # knees aim straight at the chest as the body turns - not bent outwards (owner, 2026-11-11)
                    wv = D.v("tuck", f)
                    pole = Rhip @ Vector(((0.25 if side == "R" else -0.25) * (1 - wv), 1, 0))
                knee, ank, r = ik2(s, ankle, l1, l2, pole); reach[side] = r
                Rt = chain_rot((k0 - h0).normalized(), (a0 - k0).normalized(), (knee - s).normalized(), (ank - knee).normalized())
                Rc = chain_rot((a0 - k0).normalized(), (k0 - h0).normalized() * -1, (ank - knee).normalized(), (knee - s).normalized() * -1)
                G[i] = Matrix.Translation(s) @ (Rt @ B0[th]).to_4x4()
                over[ca] = (knee, Rc); over[fo] = (ank, Rf); over[to] = (None, Rf if not grounded else Matrix.Identity(3))
        if i in over:
            pos, R = over[i]
            if pos is None: pos = G[i].translation
            G[i] = Matrix.Translation(pos) @ (R @ B0[i]).to_4x4()
        # arms: IK at the upper arm, hand targets carried by the chest
        for side in "LR":
            ua, fa, ha = IDX[f"NPC {side} UpperArm [{side}Uar]"], IDX[f"NPC {side} Forearm [{side}Lar]"], IDX[f"NPC {side} Hand [{side}Hnd]"]
            if i == ua:
                ch = IDX["NPC Spine2 [Spn2]"]
                pre = "lh" if side == "L" else "rh"
                base = (LH_GUARD if side == "L" else RH_GUARD)
                if unarmed:   # in a roll's tuck the hands go between the knees as armed, so blend back by tuck
                    base = (LH_GUARD_UNARMED if side == "L" else RH_GUARD_UNARMED).lerp(base, w)
                tgt_rest = base + Vector((D.v(pre + "_dx", f), D.v(pre + "_dy", f), D.v(pre + "_dz", f)))
                tgt = G[ch] @ (G0[ch].inverted() @ tgt_rest)
                pg = getattr(D, "pole", None)
                if pg is not None:                     # our own pole / blade grip (2026-11-12, weapon-type sets)
                    tgt = pole_wrist_target(pg, side, G[ch], G0[ch])
                s = G[i].translation
                s0, e0, w0 = P0(BN[ua]), P0(BN[fa]), P0(BN[ha])
                l1, l2 = (e0 - s0).length, (w0 - e0).length
                pole_rest = Vector((-1 if side == "L" else 1, -0.3, -1.2))
                if unarmed:          # elbows kept down under a raised open guard, not flared out to the side
                    pole_rest = Vector((-0.5 if side == "L" else 0.5, -0.4, -1.6))
                pole = G[ch].to_3x3() @ B0[ch].transposed() @ pole_rest
                el, wr, r = ik2(s, tgt, l1, l2, pole); reach["arm" + side] = r
                Ru = chain_rot((e0 - s0).normalized(), (w0 - e0).normalized(), (el - s).normalized(), (wr - el).normalized())
                Rl = chain_rot((w0 - e0).normalized(), -(e0 - s0).normalized(), (wr - el).normalized(), -(el - s).normalized())
                G[i] = Matrix.Translation(s) @ (Ru @ B0[ua]).to_4x4()
                over[fa] = (el, Rl)
        if name == "Weapon" and getattr(D, "pole", None) is not None:
            G[i] = Matrix.Translation(G[i].translation) @ pole_frame(D.pole, G[IDX["NPC Spine2 [Spn2]"]], G0[IDX["NPC Spine2 [Spn2]"]]).to_4x4()
        # head level and facing forward: neck takes half of the chest's rotation back out, the head all of it
        if name == "NPC Neck [Neck]":
            acc = (G[par].to_3x3() @ B0[par].transposed()).to_quaternion()
            Rn = acc.slerp(Quaternion(), 0.5 * (1 - w)).to_matrix()      # in a roll the head follows the body
            if D.roll: Rn = Rn @ Rax('X', -D.v("neck_tuck", f))            # ... and tucks, chin to chest
            G[i] = Matrix.Translation(G[i].translation) @ (Rn @ B0[i]).to_4x4()
        if name == "NPC Head [Head]":
            acc = (G[i].to_3x3() @ B0[i].transposed()).to_quaternion()
            Rh = acc.slerp(Quaternion(), 1 - w).to_matrix()
            if D.roll: Rh = Rh @ Rax('X', -D.v("head_tuck", f))
            G[i] = Matrix.Translation(G[i].translation) @ (Rh @ B0[i]).to_4x4()
    return G, reach, feet

# ------------------------------------------------------------------------------------------------ build stage
def clear_scene():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    for a in list(bpy.data.actions): bpy.data.actions.remove(a)

def build(D):
    clear_scene()
    sc = bpy.context.scene
    NF = D.nf
    sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = NF
    arma = import_armature()
    arma.data.display_type = 'STICK'
    # the root path from the motion data, on an empty the armature rides (preview only - not part of the clip)
    mr = bpy.data.objects.new("MotionData_Root (preview travel)", None); sc.collection.objects.link(mr)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'     # motion data is read linearly
    for t, x, y in D.motion:
        mr.location = (x, y, 0); mr.keyframe_insert("location", frame=1 + t * FPS)
    arma.parent = mr
    action = bpy.data.actions.new(f"StepDodge{D.name}")
    arma.animation_data_create(); arma.animation_data.action = action
    for b in arma.data.bones:
        try: b.select = False
        except Exception: pass
    Cfix = {}
    worst = 0
    for b in arma.data.bones:
        i = IDX[b.name]; Cfix[i] = G0[i].inverted() @ b.matrix_local
        worst = max(worst, max(abs(Cfix[i][r][c] - (1 if r == c else 0)) for r in range(4) for c in range(4)))
    say("bone-vs-skeleton rest frame max deviation:", round(worst, 5))
    prevq = {}
    reach_log = []
    for f in range(NF):
        G, reach, feet = solve_pose(D, f)
        reach_log.append({k_: round(v, 3) for k_, v in reach.items()})
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
    say(D.name, "leg/arm reach (target distance / chain length, >1 means clamped):")
    for f, r in enumerate(reach_log): say("  f%02d" % f, r)
    action.use_frame_range = True; action.frame_start = 1; action.frame_end = NF
    for t, name in D.ann:
        fr = 1 + round(t * FPS)
        action.pose_markers.new(name).frame = fr
        sc.timeline_markers.new(name, frame=fr)
    bpy.context.view_layer.objects.active = arma; arma.select_set(True)
    hkx = os.path.join(OUT, f"{D.file}.hkx")
    # PyNifly writes originalSkeletonName "Root"; vanilla clips (and the reference) say "NPC Root [Root]"
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
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{D.file}.blend"))

# ------------------------------------------------------------------------------------------------ verify stage
def verify(D):
    out = {}
    ours = AS.load_skyrim_animation(os.path.join(OUT, f"{D.file}.hkx"))
    # a diagonal has no reference clip (the older four-way set has none): compare it with itself, so the check still runs
    ref = AS.load_skyrim_animation(D.ref) if os.path.exists(D.ref) else ours
    for nm, a in (("ours", ours), ("reference", ref)):
        out[nm] = dict(duration=round(a.duration, 4), frames=a.num_frames, fps=round(1 / a.frame_duration, 3),
                       tracks=a.num_tracks, blend_hint=a.blend_hint, skeleton_name=a.original_skeleton_name,
                       binding=len(a.track_to_bone_indices),
                       annotations=[(round(x.time, 4), x.text) for x in a.annotations])
    # re-import with PyNifly onto a fresh armature and check bones, duration, markers and pose
    clear_scene()
    bpy.context.scene.render.fps = FPS
    arma = import_armature("Verify_Skeleton")
    bpy.context.view_layer.objects.active = arma; arma.select_set(True)
    r = bpy.ops.import_scene.pynifly_hkx(filepath=os.path.join(OUT, f"{D.file}.hkx"))
    act = arma.animation_data.action
    out["reimport"] = dict(result=str(r), action=act.name, frame_range=list(act.frame_range),
                           markers=sorted([(m.frame, m.name) for m in act.pose_markers]),
                           armature_bones=len(arma.data.bones),
                           bones_match_skeleton=sorted(b.name for b in arma.data.bones) == sorted(BN),
                           hkx_bone_list_matches_skeleton_order=arma.get('PYN_HKX_BONES', '').split(';') == BN)
    # compare re-imported pose with the solver at a few frames (world positions of key joints)
    errs = []
    for f in sorted({0, D.nf // 4, D.nf // 2, 3 * D.nf // 4, D.nf - 1}):
        bpy.context.scene.frame_set(f + 1)
        G, _, _ = solve_pose(D, f)
        for nm in ("NPC COM [COM ]", "NPC L Foot [Lft ]", "NPC R Foot [Rft ]", "NPC L Hand [LHnd]", "NPC R Hand [RHnd]", "NPC Head [Head]"):
            pb = arma.pose.bones[nm]
            errs.append(((arma.matrix_world @ pb.matrix).translation - G[IDX[nm]].translation).length)
    out["reimport"]["max_joint_error_units"] = round(max(errs), 4)
    names_in_tracks = len(ours.tracks) == len(BN)
    out["track_count_equals_skeleton"] = names_in_tracks
    # which tracks actually move in ours
    def moving(a):
        m = []
        for i, t in enumerate(a.tracks):
            dt = max(math.dist(t.translations[0], x) for x in t.translations)
            dr = max(1 - abs(sum(p * q for p, q in zip(t.rotations[0], x))) for x in t.rotations)
            if dt > 0.01 or dr > 1e-6: m.append(BN[i])
        return m
    def translating(a):
        return [BN[i] for i, t in enumerate(a.tracks) if max(math.dist(t.translations[0], x) for x in t.translations) > 0.01]
    for nm, a in (("ours", ours), ("reference", ref)):
        out[nm]["animated_bones"] = moving(a); out[nm]["translating_bones"] = translating(a)
        out[nm]["root_track_static"] = BN[0] not in moving(a)
    ra, oa = out["reference"]["annotations"], out["ours"]["annotations"]
    out["annotations_match_reference"] = (len(ra) == len(oa) and
        all(r_[1] == o_[1] and abs(r_[0] - o_[0]) < 0.002 for r_, o_ in zip(ra, oa)))
    out["duration_matches_motion_data"] = abs(out["ours"]["duration"] - D.duration) < 0.001
    json.dump(out, open(os.path.join(OUT, f"_verify_{D.name}.json"), "w"), indent=1)
    say(json.dumps(out, indent=1))

# ------------------------------------------------------------------------------------------------ render stage
# (node, kind, along +Y from, to, thickness) per grip set; kind box / disc / ball
PROXIES = {
    "OneHanded":          [("Weapon", "box", -6, 80, 2.0)],
    "OneHandedShield":    [("Weapon", "box", -6, 80, 2.0), ("Shield", "disc", 0, 0, 24.0)],
    "DualWield":          [("Weapon", "box", -6, 80, 2.0), ("Shield", "box", -6, 80, 2.0)],
    "Greatsword":         [("Weapon", "box", -14, 115, 2.5)],
    "BattleaxeWarhammer": [("Weapon", "box", -20, 95, 2.5), ("Weapon", "head", 80, 98, 9.0)],
    "Bow":                [("Weapon", "box", -60, 60, 2.5)],
    "Crossbow":           [("Weapon", "box", -10, 55, 6.0)],
    "Staff":              [("Weapon", "box", -45, 95, 2.5)],
    "MagicRight":         [("NPC R MagicNode [RMag]", "ball", 0, 0, 5.0)],
    "MagicLeft":          [("NPC L MagicNode [LMag]", "ball", 0, 0, 5.0)],
    "MagicBoth":          [("NPC R MagicNode [RMag]", "ball", 0, 0, 5.0), ("NPC L MagicNode [LMag]", "ball", 0, 0, 5.0)],
}

# The game's own weapon meshes for the review renders (render only; never shipped): unpacked from Skyrim - Meshes0/1.bsa
# into SIMPLEDODGE_VANILLA_MESHES (default ../_work/vanilla-meshes/meshes). Each nif is placed in its node's frame,
# as the game attaches it. Spell hands have no mesh and keep the ball stand-in.
VANILLA_MESHES = os.environ.get("SIMPLEDODGE_VANILLA_MESHES", os.path.join(os.path.dirname(HERE), "_work", "vanilla-meshes", "meshes"))
WEAPON_MESHES = {
    "OneHanded":          [("Weapon", "weapons/iron/longsword.nif")],
    "Dagger":             [("Weapon", "weapons/iron/irondagger.nif")],
    "OneHandedShield":    [("Weapon", "weapons/iron/longsword.nif"), ("Shield", "armor/iron/shield.nif")],
    "DualWield":          [("Weapon", "weapons/iron/longsword.nif"), ("Shield", "weapons/iron/longsword.nif")],
    "Greatsword":         [("Weapon", "weapons/iron/ironclaymore.nif")],
    "BattleaxeWarhammer": [("Weapon", "weapons/iron/ironbattleaxe.nif")],
    "Warhammer":          [("Weapon", "weapons/iron/warhammer.nif")],
    "Bow":                [("Weapon", "weapons/iron/ironbow.nif")],
    "Crossbow":           [("Weapon", "dlc01/weapons/crossbow/crossbow.nif")],
    "Staff":              [("Weapon", "weapons/iron/tempironstaff.nif")],
}

# the Animated Armoury weapon meshes, for the review renders of the new types only (render only, never shipped; the
# owner's download, SIMPLEDODGE_ARMOURY_MESHES)
ARMOURY_MESHES = os.environ.get("SIMPLEDODGE_ARMOURY_MESHES", r"D:\Claude output\_work\untrusted-downloads\nexus-35978-236456\x\AnimatedArmouryDAR SSE\Data\Meshes\weapons\NewArmoury")
WEAPON_MESHES.update({
    "Halberd":  [("Weapon", os.path.join(ARMOURY_MESHES, "Halberds", "IronHalberd.nif"))],
    "Pike":     [("Weapon", os.path.join(ARMOURY_MESHES, "Pikes", "IronPike.nif"))],
    "QtrStaff": [("Weapon", os.path.join(ARMOURY_MESHES, "QuarterStaffs", "ImperialStaff.nif"))],
    "Rapier":   [("Weapon", os.path.join(ARMOURY_MESHES, "Rapier", "IronRapier.nif"))],
    "Katana":   [("Weapon", os.path.join(ARMOURY_MESHES, "Katana", "IronKatana.nif"))],
    "Claws":    [("Weapon", os.path.join(ARMOURY_MESHES, "Fists", "IronClaw.nif")), ("Shield", os.path.join(ARMOURY_MESHES, "Fists", "IronClawLft.nif"))],
})

def _import_nif_meshes(path):
    before = set(bpy.data.objects)
    for o in bpy.context.selected_objects: o.select_set(False)
    bpy.context.view_layer.objects.active = None
    bpy.ops.import_scene.pynifly(filepath=path, blender_xf=False, rename_bones=False, rename_bones_niftools=False,
                                 rotate_bones_pretty=False, import_animations=False, import_collisions=False,
                                 import_tris=False, import_shapekeys=False)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    keep = []
    for o in meshes:
        mw = o.matrix_world.copy()
        for m in list(o.modifiers): o.modifiers.remove(m)
        o.parent = None; o.matrix_world = mw
        keep.append(o)
    for o in new:
        if o not in keep: bpy.data.objects.remove(o)
    return keep

def add_weapon_proxies(D, arma):
    show = getattr(D, "weapon_show", None) or getattr(D, "grip_set", None)
    meshes = WEAPON_MESHES.get(show)
    if meshes:
        sc = bpy.context.scene; sc.frame_set(1)
        for node, rel in meshes:
            path = rel if os.path.isabs(rel) else os.path.join(VANILLA_MESHES, *rel.split("/"))   # absolute: render_reference
            if not os.path.exists(path): say("weapon mesh missing", path); print("weapon mesh missing", path); continue
            pb = arma.pose.bones[node]
            W = arma.matrix_world @ pb.matrix
            for o in _import_nif_meshes(path):
                local = o.matrix_world.copy()
                o.name = "Proxy_" + o.name
                o.parent = arma; o.parent_type = 'BONE'; o.parent_bone = node
                o.matrix_world = W @ local
        return
    spec = PROXIES.get(show)
    if not spec: return
    sc = bpy.context.scene; sc.frame_set(1)
    mat = bpy.data.materials.new("weapon"); mat.diffuse_color = (0.30, 0.42, 0.62, 1)
    for node, kind, a, b, th in spec:
        if kind != "ball": continue          # only the spell hands still use stand-ins
        pb = arma.pose.bones[node]
        W = arma.matrix_world @ pb.matrix
        if kind in ("box", "head"):
            bpy.ops.mesh.primitive_cube_add(size=1)
            o = bpy.context.object
            sx, sz = (th, th) if kind == "box" else (th * 2.2, th * 0.6)
            local = Matrix.Translation(Vector((0, (a + b) / 2, 0))) @ Matrix.Diagonal((sx, b - a, sz, 1))
        elif kind == "disc":
            bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=1, vertices=32)
            o = bpy.context.object
            local = Matrix.Diagonal((th, th, 2.0, 1))
        else:
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=16, ring_count=8)
            o = bpy.context.object
            local = Matrix.Diagonal((th, th, th, 1))
        o.name = "Proxy_" + node.replace(" ", "_")
        o.parent = arma; o.parent_type = 'BONE'; o.parent_bone = node
        o.matrix_world = W @ local
        o.data.materials.clear(); o.data.materials.append(mat)

def render(D):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, f"{D.file}.blend"))
    NF = D.nf; T = D.root(NF - 1); C = T / 2
    sc = bpy.context.scene
    arma = bpy.data.objects["StepDodge_Skeleton"]; mr = arma.parent
    sc.frame_set(1)
    # body: import each HIMBO mesh, then hand its skin over to our armature
    arma.data.pose_position = 'REST'
    for nif in BODY_NIFS:
        before = set(bpy.data.objects)
        for o in bpy.context.selected_objects: o.select_set(False)
        bpy.context.view_layer.objects.active = None
        bpy.ops.import_scene.pynifly(filepath=os.path.join(BODY_DIR, nif), blender_xf=False, rename_bones=False,
                                     rename_bones_niftools=False, rotate_bones_pretty=False, import_animations=False,
                                     import_collisions=False, import_tris=False, import_shapekeys=False)
        new = [o for o in bpy.data.objects if o not in before]
        for o in new:
            if o.type == 'MESH':
                mw = o.matrix_world.copy()          # bind placement; our armature sits at the origin on frame 1
                for m in o.modifiers:
                    if m.type == 'ARMATURE': m.object = arma
                o.parent = arma; o.parent_type = 'OBJECT'
                o.matrix_parent_inverse = Matrix.Identity(4); o.matrix_basis = mw
                say("body mesh", o.name, len(o.data.vertices), "verts, groups", len(o.vertex_groups))
        for o in new:
            if o.type == 'ARMATURE': bpy.data.objects.remove(o)
            elif o.type == 'EMPTY' and not o.children: bpy.data.objects.remove(o)
    arma.data.pose_position = 'POSE'
    # simple head: a sphere on the head bone (the body meshes carry no head)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=24, ring_count=16)
    head = bpy.context.object; head.name = "PreviewHead"
    head.scale = (5.6, 6.4, 7.2)
    hb = arma.data.bones["NPC Head [Head]"]
    head.parent = arma; head.parent_type = 'BONE'; head.parent_bone = hb.name
    sc.frame_set(1)
    hw = arma.matrix_world @ arma.pose.bones[hb.name].matrix
    head.matrix_world = Matrix.Translation(hw.translation + Vector((0, 1.0, 3.6))) @ Matrix.Diagonal((6.0, 7.0, 8.2, 1))
    bpy.ops.object.shade_smooth()
    # nose so facing direction reads
    bpy.ops.mesh.primitive_cone_add(radius1=1.2, depth=3)
    nose = bpy.context.object; nose.name = "PreviewNose"
    nose.parent = arma; nose.parent_type = 'BONE'; nose.parent_bone = hb.name
    nose.matrix_world = Matrix.Translation(hw.translation + Vector((0, 8.2, 4.2))) @ Rax('X', -90).to_4x4()
    # weapon stand-ins for the grip sets (render only; nothing ships): plain boxes and discs on the Weapon / Shield /
    # magic nodes, the length along the node's +Y, so the carried weapon and any clipping through the body read
    add_weapon_proxies(D, arma)
    # look: Workbench solid grey, neutral grey world, floor with a grid so foot plants read
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'SINGLE'; sh.single_color = (0.72, 0.70, 0.67)
    sh.show_shadows = True; sh.show_cavity = True; sh.cavity_type = 'WORLD'
    sh.background_type = 'VIEWPORT'; sh.background_color = (0.42, 0.42, 0.42)
    try: sc.display.shadow_focus = 0.2
    except Exception: pass
    bpy.ops.mesh.primitive_plane_add(size=1, location=(C.x, C.y, -0.05)); fl = bpy.context.object; fl.name = "Floor"
    fl.scale = (1400, 1400, 1)
    mat = bpy.data.materials.new("floor"); mat.diffuse_color = (0.50, 0.50, 0.50, 1); fl.data.materials.append(mat)
    # grid lines every 20 units across x (shows plants vs. slide)
    gm = bpy.data.materials.new("grid"); gm.diffuse_color = (0.33, 0.33, 0.33, 1)
    x0, x1 = min(0, T.x) - 80, max(0, T.x) + 80; y0, y1 = min(0, T.y) - 80, max(0, T.y) + 80
    for gx in range(int(x0 // 20) * 20, int(x1) + 1, 20):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(gx, C.y, 0.0)); c = bpy.context.object
        c.scale = (0.5, y1 - y0, 0.12); c.data.materials.append(gm)
    for gy in range(int(y0 // 20) * 20, int(y1) + 1, 20):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(C.x, gy, 0.0)); c = bpy.context.object
        c.scale = (x1 - x0, 0.5, 0.12); c.data.materials.append(gm)
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name not in ("Floor",) and not o.data.materials:
            pass
    sh.color_type = 'MATERIAL'
    bodymat = bpy.data.materials.new("body"); bodymat.diffuse_color = (0.74, 0.71, 0.67, 1)
    for o in bpy.data.objects:
        if o.type == 'MESH' and (o.parent == arma) and not o.name.startswith("Proxy_"):
            o.data.materials.clear(); o.data.materials.append(bodymat)
    nm = bpy.data.materials.new("nose"); nm.diffuse_color = (0.55, 0.35, 0.30, 1); nose.data.materials.clear(); nose.data.materials.append(nm)
    sc.render.resolution_x = 960; sc.render.resolution_y = 540; sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    # cameras: front (static, sees the whole lateral travel), side (rides the root, from the actor's left)
    def cam(name, loc, rot, ortho, parent=None):
        cd = bpy.data.cameras.new(name); cd.type = 'ORTHO'; cd.ortho_scale = ortho
        co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co)
        co.location = loc; co.rotation_euler = rot
        if parent: co.parent = parent
        return co
    # wide front: static, the whole lateral travel; close front and close side ride the root (motion data)
    if abs(T.x) >= abs(T.y):     # lateral travel: wide view from the front
        wide = cam("CamWide", (C.x, 600, 150), (radians(80), 0, radians(180)), abs(T.x) + 80)
    else:                        # forward/back travel: wide view from the actor's left side
        wide = cam("CamWide", (-600, C.y, 150), (radians(80), 0, radians(-90)), abs(T.y) + 110)
    front = cam("CamFront", (0, 600, 66), (radians(90), 0, radians(180)), 150, parent=mr)
    side = cam("CamSide", (-600, 0, 66), (radians(90), 0, radians(-90)), 150, parent=mr)
    RES = {"CamWide": (1440, 540), "CamFront": (720, 720), "CamSide": (720, 720)}
    frames_dir = os.path.join(OUT, "_frames", D.name); os.makedirs(frames_dir, exist_ok=True)
    # contact metrics on the evaluated feet mesh: lowest point per frame, and drift of the planted foot
    dg = bpy.context.evaluated_depsgraph_get()
    feet_obj = [o for o in bpy.data.objects if o.type == 'MESH' and 'feet' in o.name.lower()]
    for f in range(1, NF + 1):
        sc.frame_set(f)
        if feet_obj:
            ev = feet_obj[0].evaluated_get(dg); me = ev.to_mesh()
            zs = [(ev.matrix_world @ v.co) for v in me.vertices]
            lz = min(zs, key=lambda p: p.z)
            say(D.name, "frame %02d feet lowest z %.2f at (%.1f, %.1f)" % (f, lz.z, lz.x, lz.y)); ev.to_mesh_clear()
        for c in (front, side, wide):
            sc.camera = c
            sc.render.resolution_x, sc.render.resolution_y = RES[c.name]
            sc.render.filepath = os.path.join(frames_dir, f"{c.name}_{f:03d}.png")
            bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"_preview_{D.name}.blend"))

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stages = [a_ for a_ in args if a_ in ("build", "verify", "render")] or ["build", "verify", "render"]
    dirs = [a_ for a_ in args if a_ in DESIGNS] or list(DESIGNS)
    for d in dirs:
        for st in stages:
            {"build": build, "verify": verify, "render": render}[st](DESIGNS[d])
    _tag = '_'.join(dirs) if len(dirs) <= 4 else f"{dirs[0]}_and_{len(dirs) - 1}_more"   # a long list overran MAX_PATH
    open(os.path.join(OUT, f"_log_{'_'.join(stages)}_{_tag}.txt"), "w").write("\n".join(log))
