# interleaved_to_spline.py - lets PyNifly's importer show a clip stored as hkaInterleavedUncompressedAnimation (it reads
# only spline-compressed clips) by rewriting it as a spline clip, for LOOKING at another mod's animation in Blender
# (render_reference.py). Viewing aid only: the output is a scratch file, never shipped, never a source for our poses.
# Run inside Blender's Python (needs io_scene_nifly):
#   blender --background --factory-startup --python interleaved_to_spline.py -- <in.hkx> <out.hkx>
import sys, struct
args = sys.argv[sys.argv.index("--") + 1:]
src, dst = args[0], args[1]
from io_scene_nifly.hkx import anim_skyrim as AS
from io_scene_nifly.hkx.anim_fo4 import AnimationData, TrackData

data = open(src, "rb").read()
ptr = data[0x10]
secs = AS._parse_hkx_sections(data)
ds = secs["__data__"]; data_abs = ds["offset"]
fx = AS._parse_local_fixups(data, ds)
objs = AS._parse_virtual_fixups(data, ds, secs["__classnames__"]["offset"])
rel = next(r for r, c in objs if c == "hkaInterleavedUncompressedAnimation")
a = data_abs + rel
base = 2 * ptr; arr = ptr + 8
duration = struct.unpack_from("<f", data, a + base + 4)[0]
ntracks = struct.unpack_from("<I", data, a + base + 8)[0]
o_ann = base + 16 + ptr
o_tr = (o_ann + arr + ptr - 1) & ~(ptr - 1)
count = struct.unpack_from("<I", data, a + o_tr + ptr)[0]
content = fx[rel + o_tr]
nframes = count // ntracks
anim = AnimationData()
anim.duration = duration; anim.num_tracks = ntracks; anim.num_frames = nframes
anim.frame_duration = duration / max(1, nframes - 1)
anim.tracks = [TrackData() for _ in range(ntracks)]
for f in range(nframes):
    for t in range(ntracks):
        o = data_abs + content + (f * ntracks + t) * 48
        v = struct.unpack_from("<12f", data, o)
        tr = anim.tracks[t]
        tr.translations.append(list(v[0:3])); tr.rotations.append(list(v[4:8])); tr.scales.append(list(v[8:11]))
for r2, c in objs:   # keep the binding's skeleton name and track map if present
    if c == "hkaAnimationBinding":
        n = fx.get(r2 + 2 * ptr)
        if n is not None:
            anim.original_skeleton_name = AS._read_null_string(data, data_abs + n)
anim.original_skeleton_name = anim.original_skeleton_name or "NPC Root [Root]"
anim.bone_names = [""] * ntracks
AS.write_skyrim_animation(dst, anim, ptr_size=8)
print("converted", src, "->", dst, ntracks, "tracks", nframes, "frames", round(duration, 3), "s")
