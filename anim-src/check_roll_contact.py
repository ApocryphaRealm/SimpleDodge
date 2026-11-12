# check_roll_contact.py - per roll clip, the lowest height above the floor of the head, the neck and the back (spine
# joints) over the whole clip, from the same solver the clips are built with. The owner (2026-11-11): the head must
# never hit the ground in a roll; at most the back of the neck, preferably only the back.
# Run: blender --background --factory-startup --python check_roll_contact.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_stepdodge as B
for k in ("RollLeft", "RollRight", "RollForward", "RollBack"):
    D = B.DESIGNS[k]
    low = {"crown": (1e9, 0), "head": (1e9, 0), "neck": (1e9, 0), "back": (1e9, 0)}
    for f in range(D.nf):
        G, _, _ = B.solve_pose(D, f)
        z = B.head_crown(G).z
        if z < low["crown"][0]: low["crown"] = (z, f)
        for i, n in enumerate(B.BN):
            part = "head" if "Head [Head]" in n else "neck" if "Neck" in n else "back" if "Spine" in n else None
            if part and G[i].translation.z < low[part][0]:
                low[part] = (G[i].translation.z, f)
    print("CONTACT", k, " ".join(f"{p} {z:.1f} (f{f})" for p, (z, f) in low.items()))
