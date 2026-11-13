"""Shorter step distance - the installer's 'Step distance: Shorter' option (1.2.0, 2026-11-12).

Without Animation Motion Revolution a dodge travels by the animationdatasinglefile MOTION DATA of its clip generator's
name (with it, by the clip's own animmotion annotations - make_clip_motion.py keeps the two equal). This
writes a copy of the step entries sdge$0..sdge$7 (DefaultMale~1 and DefaultFemale~1) with every root-motion key
scaled per axis:  forward (y > 0) x0.7, back (y < 0) x0.6, sideways (x) x0.8 - the factors of TK Dodge Shorter Step
Distance (Nexus 186555): forward 409.3 -> 286.5, back 300 -> 180, sides ~251.5 -> 201. A diagonal (sdge$4..7) has
both an x and a y part, so each part takes its own direction's factor (forward-left: x0.8 sideways, x0.7 forward).

  sdge$0 forward, $1 back, $2 left, $3 right   - shared by the step dodges AND the standard (not long) rolls, which
                                                use the same clip-generator names; so the standard roll is shorter too
  sdge$4..7 diagonals                          - step dodges only
  sdge$8..11 long rolls                         - not touched
  FirstPerson~1 346 back, 347 left, 348 right, 791 forward - the first-person rolls; round 2 (2026-11-13) measured
                                                first person unchanged by Shorter because these were left out
  FirstPerson~1 sdge$0..3                       - the first-person diagonals (2026-11-13), the third-person diagonal
                                                motion under the first-person project's own ids

With Animation Motion Revolution the clips' own annotations move the character instead of this motion data, so the
option also ships scaled clips: make_clip_motion.py writes them (fomod-options/Step-Shorter/Meshes).

Times, key count, rotation block and line endings are kept. The output goes to fomod-options\\Step-Shorter, the
package-root folder the FOMOD option installs over Common\\ (priority 1).
Usage: python make_shorter_steps.py
"""
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(REPO, "dist", "Nemesis_Engine", "mod", "sdge", "animationdatasinglefile")
DST = os.path.join(REPO, "fomod-options", "Step-Shorter", "Nemesis_Engine", "mod", "sdge", "animationdatasinglefile")
FORWARD, BACK, SIDE = 0.7, 0.6, 0.8
ENTRIES = {"DefaultMale~1": ["sdge$%d" % n for n in range(0, 8)],
           "DefaultFemale~1": ["sdge$%d" % n for n in range(0, 8)],
           "FirstPerson~1": ["346", "347", "348", "791"] + ["sdge$%d" % n for n in range(0, 4)]}


def scale(tok, f):
    v = float(tok)
    if abs(v) < 1e-3:
        return tok  # keep zero and float noise exactly as written
    return "%.1f" % (v * f)


def main():
    for project, entries in ENTRIES.items():
        os.makedirs(os.path.join(DST, project), exist_ok=True)
        for n in entries:
            name = n + ".txt"
            raw = open(os.path.join(SRC, project, name), "rb").read().decode("ascii")
            nl = "\r\n" if "\r\n" in raw else "\n"
            lines = raw.split(nl)
            assert lines[0] == n, (project, name, lines[0])
            count = int(lines[2])
            out = lines[:3]
            last = None
            for k in range(3, 3 + count):
                t, x, y, z = lines[k].split(" ")
                out.append(" ".join((t, scale(x, SIDE), scale(y, FORWARD if float(y) > 0 else BACK), z)))
                last = out[-1]
            out += lines[3 + count:]
            open(os.path.join(DST, project, name), "wb").write(nl.join(out).encode("ascii"))
            print("%s %s end %s" % (project, name, last))


if __name__ == "__main__":
    main()
