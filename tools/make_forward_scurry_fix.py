"""Write the "Forward dodge scurry fix" installer option (1.4.0).

In the third-person behaviour patch the forward clips' trigger arrays fire TKDodgeStop 0.300 s before the clip ends,
against 0.080 s on the back step. TKDodgeStop hands the dodge over to locomotion, so a forward dodge is cut 0.3 s
early, and a dodge animation set that holds a short pause at its end (Dynamic Dodge Animation) "scurries" - the legs
start running while the dodge pose is still settling. The option ships copies of only those trigger arrays with
TKDodgeStop at -0.080 (the back step's value); nothing else in them changes. First person is already even.

    1hm_behavior  #sdge$33 (forward step)   #sdge$35 (forward rolls; also the back-diagonal rolls)
    mt_behavior   #sdge$33                  #sdge$35
    magicbehavior #sdge$35 (forward step)   #sdge$37 (forward rolls; also the back-diagonal rolls)

Run from the repo: py -3 tools/make_forward_scurry_fix.py  - writes fomod-options/Forward-Scurry-Fix and checks that
each copy differs from dist/ in exactly one line.
"""
import os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "dist", "Nemesis_Engine", "mod", "sdge")
DST = os.path.join(REPO, "fomod-options", "Forward-Scurry-Fix", "Nemesis_Engine", "mod", "sdge")
FILES = [("1hm_behavior", "#sdge$33.txt"), ("1hm_behavior", "#sdge$35.txt"),
         ("mt_behavior", "#sdge$33.txt"), ("mt_behavior", "#sdge$35.txt"),
         ("magicbehavior", "#sdge$35.txt"), ("magicbehavior", "#sdge$37.txt")]
OLD = b'<hkparam name="localTime">-0.300000</hkparam>'
NEW = b'<hkparam name="localTime">-0.080000</hkparam>'

for d, f in FILES:
    src = os.path.join(SRC, d, f)
    data = open(src, "rb").read()
    lines = data.split(b"\n")
    # the TKDodgeStop trigger: a -0.300 localTime whose event id (3 lines on) is TKDodgeStop, relative to clip end
    hits = [i for i, l in enumerate(lines) if OLD in l and b"$eventID[TKDodgeStop]$" in lines[i + 3]
            and b'"relativeToEndOfClip">true' in b"".join(lines[i:i + 10])]
    if len(hits) != 1:
        sys.exit(f"FAIL {d}\\{f}: expected one TKDodgeStop trigger at -0.300, found {len(hits)}")
    lines[hits[0]] = lines[hits[0]].replace(OLD, NEW)
    out = b"\n".join(lines)
    changed = [i for i, (a, b) in enumerate(zip(data.split(b"\n"), out.split(b"\n"))) if a != b]
    assert len(changed) == 1 and len(out) == len(data), (d, f, changed)
    os.makedirs(os.path.join(DST, d), exist_ok=True)
    open(os.path.join(DST, d, f), "wb").write(out)
    print(f"ok  {d}\\{f}: line {hits[0] + 1} TKDodgeStop -0.300 -> -0.080 (one line changed)")
