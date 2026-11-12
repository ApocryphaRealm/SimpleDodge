# hero_composite.py - builds the Simple Dodge identity banner (1920x1080) from hero_render.py's frames: the last frame
# solid, the earlier ones ghosted behind it (each cut out against the empty plate), framed in the Skyrim banner rim.
# Run: py -3 hero_composite.py <Design> <out.png> <frame> [<frame> ...]   (last frame = the solid one)
import os, sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
design, out, frames = sys.argv[1], sys.argv[2], [int(a) for a in sys.argv[3:]]
src = os.path.join(HERE, "_hero", design)
plate = Image.open(os.path.join(src, "plate.png")).convert("RGB")
canvas = plate.copy()
for i, f in enumerate(frames):
    im = Image.open(os.path.join(src, f"{f:03d}.png")).convert("RGB")
    m = ImageChops.difference(im, plate).convert("L").point(lambda v: 255 if v > 10 else 0).filter(ImageFilter.MaxFilter(3))
    m = m.filter(ImageFilter.GaussianBlur(1.2))
    a = 1.0 if i == len(frames) - 1 else 0.22 + 0.5 * i / max(1, len(frames) - 1)
    canvas = Image.composite(im, canvas, m.point(lambda v: int(v * a)))
d = ImageDraw.Draw(canvas); W, H = canvas.size; RIM = (245, 242, 233)
d.rectangle([0, 0, W - 1, H - 1], outline=RIM, width=3)
d.rectangle([16, 16, W - 17, H - 17], outline=tuple(int(v * 0.35 + 5 * 0.65) for v in RIM), width=1)
canvas.save(out); print(out, canvas.size)
