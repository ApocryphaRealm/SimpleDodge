# make_previews.py - turns the frames build_stepdodge.py rendered (_frames\<Dir>\) into the review files:
#   StepDodge<Dir>_preview.mp4 - [close front | close side] over the wide travel view; 3 plays at speed, 1 at 1/3
#   StepDodge_contact_sheet.png - rows Left, Right, Forward, Back (top to bottom), 8 evenly spaced frames, each frame = close front + side
# Needs ffmpeg on PATH. Run: py -3 make_previews.py        (rolls: py -3 make_previews.py rolls -> Roll_contact_sheet.png)
import os, subprocess, glob, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROLLS = "rolls" in sys.argv[1:]; UN = "Unarmed" if "unarmed" in sys.argv[1:] else ""
DIAG = "diag" in sys.argv[1:]
DIRS = [d + UN for d in (["RollLeft", "RollRight", "RollForward", "RollBack"] if ROLLS else ["ForwardLeft", "ForwardRight", "BackLeft", "BackRight"] if DIAG else ["Left", "Right", "Forward", "Back"])]
SHEET = ("Roll" if ROLLS else "Diagonal" if DIAG else "StepDodge") + ("_unarmed" if UN else "") + "_contact_sheet.png"

def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)

rows = []
for d in DIRS:
    fd = os.path.join(HERE, "_frames", d)
    n = len(glob.glob(os.path.join(fd, "CamFront_*.png")))
    fr, sd, wd = (os.path.join(fd, f"{c}_%03d.png") for c in ("CamFront", "CamSide", "CamWide"))
    ff("-framerate", "30", "-i", fr, "-framerate", "30", "-i", sd, "-framerate", "30", "-i", wd, "-filter_complex",
       f"[0][1]hstack[t];[t][2]vstack,split[a][b];[a]loop=2:{n}:0[n];[b]setpts=3*PTS[s];[n][s]concat=n=2:v=1[o]",
       "-map", "[o]", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
       os.path.join(HERE, (f"{d}_preview.mp4" if ROLLS else f"StepDodge{d}_preview.mp4")))
    picks = [1 + round(i * (n - 1) / 7) for i in range(8)]
    ins, flt = [], []
    for j, p in enumerate(picks):
        ins += ["-i", os.path.join(fd, f"CamFront_{p:03d}.png"), "-i", os.path.join(fd, f"CamSide_{p:03d}.png")]
        flt.append(f"[{2*j}]scale=240:240[f{j}];[{2*j+1}]scale=240:240[s{j}];[f{j}][s{j}]hstack[p{j}]")
    row = os.path.join(HERE, "_frames", f"_row_{d}.png")
    ff(*ins, "-filter_complex", ";".join(flt) + ";" + "".join(f"[p{j}]" for j in range(8)) +
       "hstack=8", "-frames:v", "1", row)
    rows.append(row)
ins = []
for r in rows: ins += ["-i", r]
ff(*ins, "-filter_complex", "".join(f"[{i}]" for i in range(len(rows))) + f"vstack={len(rows)}", "-frames:v", "1",
   os.path.join(HERE, SHEET))
print("done")
