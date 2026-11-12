# inspect_rolls.py - prints duration, frames, annotations and the root/COM track travel of the roll clips the package
# carries (dodgeleft/right/back, sneakrun_forwardroll), so our own rolls can match their timing and motion.
# Run: blender --background --factory-startup --python inspect_rolls.py -- <folder with the clips>
import sys, os, json, math, addon_utils
addon_utils.enable("io_scene_nifly", default_set=True)
from io_scene_nifly.hkx import anim_skyrim as AS
d = sys.argv[sys.argv.index("--") + 1]
out = {}
for n in ("dodgeleft", "dodgeright", "dodgeback", "sneakrun_forwardroll"):
    a = AS.load_skyrim_animation(os.path.join(d, n + ".hkx"))
    tr = {}
    for i, t in enumerate(a.tracks[:3]):
        tr[i] = [[round(v, 1) for v in t.translations[k]] for k in (0, len(t.translations) // 2, -1)]
    out[n] = dict(duration=round(a.duration, 4), frames=a.num_frames, tracks=a.num_tracks,
                  annotations=[(round(x.time, 4), x.text) for x in a.annotations], first_tracks=tr,
                  bones=a.track_to_bone_indices[:3] if a.track_to_bone_indices else None)
print("ROLLJSON " + json.dumps(out))
