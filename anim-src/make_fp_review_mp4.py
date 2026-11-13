# make_fp_review_mp4.py - review clips of the first-person diagonals (2026-11-13), playable on a phone.
# Each video: the first-person camera's view (build_fp_diagonals.py's Cam1st frames) of the two straight dodges a
# diagonal is blended from, with the diagonal between them:  [straight A | DIAGONAL | straight B],  half speed,
# played 3 times, H.264 (libx264) yuv420p, +faststart. A shorter clip holds its last frame so the three stay in step.
# Also all_diagonals.mp4: the four diagonals in a 2x2 grid.
# Run: py -3 make_fp_review_mp4.py [<out dir>]        (needs ffmpeg; default out dir firstperson\mp4)
import glob, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FR = os.path.join(HERE, "firstperson", "_frames")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "firstperson", "mp4")
FONT = "C\\:/Windows/Fonts/arial.ttf"
TRIPLES = {"ForwardLeft": ("Forward", "Left"), "ForwardRight": ("Forward", "Right"),
           "BackLeft": ("Back", "Left"), "BackRight": ("Back", "Right")}


def frames(name):
    n = len(glob.glob(os.path.join(FR, name, "Cam1st_*.png")))
    assert n > 0, name
    return n


def panel(k, name, n, label):
    pad = n - frames(name)
    tp = ",tpad=stop_mode=clone:stop=%d" % pad if pad > 0 else ""
    return ("[%d]scale=640:360%s,drawtext=fontfile='%s':text='%s':x=12:y=10:fontsize=26:fontcolor=white:"
            "box=1:boxcolor=black@0.45:boxborderw=6[p%d]" % (k, tp, FONT, label, k))


def run(names, labels, layout, out):
    n = max(frames(x) for x in names)
    ins = []
    for x in names:
        ins += ["-framerate", "30", "-i", os.path.join(FR, x, "Cam1st_%03d.png")]
    parts = [panel(k, x, n, lab) for k, (x, lab) in enumerate(zip(names, labels))]
    refs = "".join("[p%d]" % k for k in range(len(names)))
    if layout == "row":
        stack = "%shstack=%d" % (refs, len(names))
    else:
        stack = "[p0][p1]hstack=2[r0];[p2][p3]hstack=2[r1];[r0][r1]vstack=2"
    flt = ";".join(parts) + ";" + stack + ",loop=2:%d:0,setpts=2*PTS,format=yuv420p[o]" % n
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", flt, "-map", "[o]", "-r", "30",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", out], check=True)
    print(out)


os.makedirs(OUT, exist_ok=True)
for d, (a, b) in TRIPLES.items():
    run([a, d, b], [a + " (game)", d + " (new)", b + " (game)"], "row", os.path.join(OUT, "FP_%s.mp4" % d))
run(list(TRIPLES), list(TRIPLES), "grid", os.path.join(OUT, "FP_all_diagonals.mp4"))
