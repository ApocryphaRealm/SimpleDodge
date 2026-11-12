"""Shorter step distance - the installer's 'Step distance: Shorter' option (1.2.0, 2026-11-12).

How far a dodge travels is the animationdatasinglefile MOTION DATA of its clip generator's name, not the .hkx. This
writes a copy of the step entries sdge$0..sdge$7 (DefaultMale~1 and DefaultFemale~1) with every root-motion key
scaled per axis:  forward (y > 0) x0.7, back (y < 0) x0.6, sideways (x) x0.8 - the factors of TK Dodge Shorter Step
Distance (Nexus 186555): forward 409.3 -> 286.5, back 300 -> 180, sides ~251.5 -> 201. A diagonal (sdge$4..7) has
both an x and a y part, so each part takes its own direction's factor (forward-left: x0.8 sideways, x0.7 forward).

  sdge$0 forward, $1 back, $2 left, $3 right   - shared by the step dodges AND the standard (not long) rolls, which
                                                use the same clip-generator names; so the standard roll is shorter too
  sdge$4..7 diagonals                          - step dodges only
  sdge$8..11 long rolls, FirstPerson~1          - not touched

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
ENTRIES = range(0, 8)


def scale(tok, f):
    v = float(tok)
    if abs(v) < 1e-3:
        return tok  # keep zero and float noise exactly as written
    return "%.1f" % (v * f)


def main():
    for project in ("DefaultMale~1", "DefaultFemale~1"):
        os.makedirs(os.path.join(DST, project), exist_ok=True)
        for n in ENTRIES:
            name = "sdge$%d.txt" % n
            raw = open(os.path.join(SRC, project, name), "rb").read().decode("ascii")
            nl = "\r\n" if "\r\n" in raw else "\n"
            lines = raw.split(nl)
            assert lines[0] == "sdge$%d" % n, (project, name, lines[0])
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
