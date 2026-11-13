# make_review_mp4.py - a before/after review clip that plays on a phone (2026-11-12, the owner's phone does not play GIFs).
# BEFORE on the left, AFTER on the right, each = close front view | close side view (build_stepdodge.py's CamFront /
# CamSide frames), at half speed, played 3 times. H.264 (libx264), yuv420p, even dimensions, +faststart.
# With "closeup" a second row shows the hands: the chest-height middle of each view, cropped and enlarged 2x.
# Run: py -3 make_review_mp4.py <before frames dir> <after frames dir> <out.mp4> [closeup]          (needs ffmpeg)
import glob, os, subprocess, sys
before, after, out = sys.argv[1:4]
closeup = "closeup" in sys.argv[4:]
n = len(glob.glob(os.path.join(before, "CamFront_*.png")))
m = len(glob.glob(os.path.join(after, "CamFront_*.png")))
assert n > 0 and n == m, (n, m)
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
ins = []
for d in (before, after):
    for c in ("CamFront", "CamSide"):
        ins += ["-framerate", "30", "-i", os.path.join(d, c + "_%03d.png")]
if not closeup:
    flt = ("[0]scale=480:480[a];[1]scale=480:480[b];[2]scale=480:480[c];[3]scale=480:480[d];"
           "[a][b][c][d]hstack=4,setpts=2*PTS,loop=2:%d:0,format=yuv420p[o]" % n)
else:
    # the 720x720 views span 150 game units around z 66: the hands at chest height sit near y 170-410 px
    parts = []
    for k, lab in enumerate("abcd"):
        parts.append("[%d]split[%s0][%s1];[%s0]scale=480:480[%s];[%s1]crop=240:240:240:170,scale=480:480[%sz]" %
                     (k, lab, lab, lab, lab, lab, lab))
    flt = (";".join(parts) + ";[a][b][c][d]hstack=4[top];[az][bz][cz][dz]hstack=4[bot];[top][bot]vstack=2,"
           "setpts=2*PTS,loop=2:%d:0,format=yuv420p[o]" % n)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", flt, "-map", "[o]", "-r", "30",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", out], check=True)
print(out)
