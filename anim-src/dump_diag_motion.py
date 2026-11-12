# dump_diag_motion.py - writes the four diagonal clips' duration, motion keys and annotations to diag_motion.json, the
# single source the behaviour patch's animationdatasinglefile entries are written from.
# Run: blender --background --factory-startup --python dump_diag_motion.py
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_stepdodge as B
out = {n: dict(file=B.DESIGNS[n].file + ".hkx", duration=B.SPEC[n]["duration"],
               motion=[[t, round(x, 4), round(y, 4)] for t, x, y in B.SPEC[n]["motion"]],
               annotations=[[t, a] for t, a in B.SPEC[n]["ann"]]) for n in B.DIAG}
json.dump(out, open(os.path.join(B.OUT, "diag_motion.json"), "w"), indent=1)
print("DIAG written", list(out))
