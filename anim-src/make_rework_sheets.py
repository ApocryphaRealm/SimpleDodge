# make_rework_sheets.py - before/after contact sheets for a step-dodge rework (2026-11-12).
# For each direction: row 1 = BEFORE (top), row 2 = AFTER (bottom), no text on the image (ffmpeg's drawtext crashes here), 8 matching frames (evenly spaced over the clip, the same frame
# numbers in both rows), each frame = close front view + close side view (build_stepdodge.py's CamFront / CamSide).
# Run: py -3 make_rework_sheets.py <before _frames dir> <after _frames dir> <out dir> [Dir ...]      (needs ffmpeg)
import os, subprocess, glob, sys
before, after, out = sys.argv[1:4]
dirs = sys.argv[4:] or ["Left", "Right", "Forward", "Back", "ForwardLeft", "ForwardRight", "BackLeft", "BackRight"]
os.makedirs(out, exist_ok=True)

def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)

def row(src, picks, path, label):
    ins, flt = [], []
    for j, p in enumerate(picks):
        ins += ["-i", os.path.join(src, f"CamFront_{p:03d}.png"), "-i", os.path.join(src, f"CamSide_{p:03d}.png")]
        flt.append(f"[{2*j}]scale=200:200[f{j}];[{2*j+1}]scale=200:200[s{j}];[f{j}][s{j}]hstack[p{j}]")
    ff(*ins, "-filter_complex", ";".join(flt) + ";" + "".join(f"[p{j}]" for j in range(len(picks))) +
       f"hstack={len(picks)}",
       "-frames:v", "1", path)

for d in dirs:
    nb = len(glob.glob(os.path.join(before, d, "CamFront_*.png")))
    na = len(glob.glob(os.path.join(after, d, "CamFront_*.png")))
    assert nb == na and nb > 0, (d, nb, na)          # same clip length before and after
    picks = [1 + round(i * (nb - 1) / 7) for i in range(8)]
    rb, ra = os.path.join(out, f"_b_{d}.png"), os.path.join(out, f"_a_{d}.png")
    row(os.path.join(before, d), picks, rb, f"{d} BEFORE  frames {picks}")
    row(os.path.join(after, d), picks, ra, f"{d} AFTER")
    ff("-i", rb, "-i", ra, "-filter_complex", "[0][1]vstack=2", "-frames:v", "1",
       os.path.join(out, f"StepDodge{d}_before_after.png"))
    os.remove(rb); os.remove(ra)
    print(d, picks)
