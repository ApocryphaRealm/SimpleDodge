"""Read and rescale the root motion a dodge clip carries in its own .hkx (1.2.0 round 3, 2026-11-13).

Why: Animation Motion Revolution (AMR, Nexus 50258 - in most combat lists) moves the character by a clip's own
"animmotion x y z" annotations whenever the clip has them, and then ignores the clip generator's motion data in
animationdatasinglefile (its Hooks.cpp: ProcessTranslationData_Hook uses the annotation list when it is not empty,
the vanilla motion data only otherwise). Every Simple Dodge clip carries those annotations. So with AMR:
  - the long roll played the standard roll's file, so it went no further (round 2, F5: 470 both);
  - the Shorter option's motion data did nothing (P2: Normal distances).
Without AMR the motion data drives the distance. A clip's annotations and its motion data must therefore say the same
thing, and every distance option needs its own clip files as well as its own motion data.

The annotation strings are rewritten IN PLACE in the packfile: each new string is no longer than the old one and is
padded with NUL bytes, so no offset, fixup or alignment in the file changes. Times are not touched.

  read(path)                          -> [(offset, room, (x, y, z))]
  final(path, duration)               -> (x, y) the annotation motion reached at `duration` (AMR's interpolation)
  rewrite(src, dst, fn)               -> writes dst with every animmotion (x, y, z) replaced by fn(x, y, z)
Usage as a script: python clip_motion.py <file.hkx> [...]   prints each file's annotation motion
"""
import os, re, struct, sys

ANN = re.compile(rb"animmotion (-?[0-9.eE+-]+) (-?[0-9.eE+-]+) (-?[0-9.eE+-]+)\x00")


def read(path):
    b = open(path, "rb").read()
    out = []
    for m in ANN.finditer(b):
        end = m.end()  # just past the NUL
        while end < len(b) and b[end] == 0:
            end += 1   # the NUL padding after the string is room too
        room = end - m.start() - 1  # keep at least one NUL
        out.append((m.start(), room, tuple(float(m.group(i)) for i in (1, 2, 3))))
    return out


def times(path):
    """The annotation times, in file order. A Skyrim hkaAnnotationTrack annotation is {float time; pad; char* text};
    the times sit before the strings as 16-byte records. They are matched to the strings by order."""
    b = open(path, "rb").read()
    anns = read(path)
    if not anns:
        return []
    first = anns[0][0]
    n = len(anns)
    # search backwards for n consecutive 16-byte records whose first float is non-decreasing from 0
    for start in range(first - 16 * n, max(0, first - 16 * n - 512), -4):
        ts = [struct.unpack_from("<f", b, start + 16 * k)[0] for k in range(n)]
        if abs(ts[0]) < 1e-6 and all(0 <= ts[k + 1] - ts[k] < 2 for k in range(n - 1)) and ts[-1] > 0:
            return ts
    raise ValueError("%s: annotation times not found" % path)


def final(path, duration):
    """Where AMR's interpolation of the annotations puts the root at `duration` (clamped to the last annotation)."""
    anns = [a[2] for a in read(path)]
    ts = times(path)
    t = min(duration, ts[-1])
    for k in range(len(ts)):
        if t <= ts[k] + 1e-6:
            if k == 0:
                return anns[0][:2]
            f = (t - ts[k - 1]) / (ts[k] - ts[k - 1]) if ts[k] > ts[k - 1] else 1.0
            return tuple(anns[k - 1][i] * (1 - f) + anns[k][i] * f for i in (0, 1))
    return anns[-1][:2]


def _fmt(v, room_for_it):
    if abs(v) < 5e-4:
        return "0"
    for prec in (6, 5, 4):
        s = "%.*g" % (prec, v)
        if "e" not in s and len(s) <= room_for_it:
            return s
    for dec in (3, 2, 1, 0):
        s = ("%.*f" % (dec, v)).rstrip("0").rstrip(".") if dec else "%d" % round(v)
        if len(s) <= room_for_it:
            return s
    raise ValueError("no room for %r" % v)


def rewrite(src, dst, fn):
    b = bytearray(open(src, "rb").read())
    for off, room, (x, y, z) in read(src):
        nx, ny, nz = fn(x, y, z)
        old_len = room
        # give each number as much room as the whole string allows
        parts = ["0", "0", "0"]
        vals = (nx, ny, nz)
        for prec_room in range(12, 0, -1):
            try:
                parts = [_fmt(v, prec_room) for v in vals]
            except ValueError:
                continue
            s = ("animmotion %s %s %s" % tuple(parts)).encode("ascii")
            if len(s) <= old_len:
                break
        else:
            raise ValueError("%s: cannot fit motion %r in %d bytes" % (src, vals, old_len))
        b[off:off + old_len + 1] = s + b"\x00" * (old_len + 1 - len(s))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "wb").write(bytes(b))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p)
        for (off, room, m), t in zip(read(p), times(p)):
            print("  %.4f  %s" % (t, " ".join("%g" % v for v in m)))
