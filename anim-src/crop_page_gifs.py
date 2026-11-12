# crop_page_gifs.py - crops the eight top-down showcase GIFs to the dodge's own path for the Nexus page (2026-11-11: in
# the 600x600 originals the character fills a small part of the frame). One crop SIZE for all eight, so the directions
# compare at the same scale; each crop is centred on that clip's own path. Originals are left as they are.
import os
from PIL import Image, ImageChops, ImageSequence
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "gif-showcase"); OUT = os.path.join(SRC, "page"); os.makedirs(OUT, exist_ok=True)
DIRS = ("Forward", "Back", "Left", "Right", "ForwardLeft", "ForwardRight", "BackLeft", "BackRight")


def path_box(gif):
    # the armour and its shadow are much darker than the light floor (the floor's dithering changes frame to frame, so
    # a frame difference catches the whole picture): the union of the dark pixels over the clip is the dodge's path
    acc = None
    for f in ImageSequence.Iterator(Image.open(gif)):
        m = f.convert("L").point(lambda v: 255 if v < 95 else 0)
        acc = m if acc is None else ImageChops.lighter(acc, m)
    return acc.getbbox()


boxes = {d: path_box(os.path.join(SRC, f"SimpleDodge-top-{d}.gif")) for d in DIRS}
side = max(max(b[2] - b[0], b[3] - b[1]) for b in boxes.values()) + 60
for d, (x0, y0, x1, y1) in boxes.items():
    im = Image.open(os.path.join(SRC, f"SimpleDodge-top-{d}.gif"))
    W, H = im.size
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    L = min(max(0, cx - side // 2), W - side); T = min(max(0, cy - side // 2), H - side)
    frames, durs = [], []
    for f in ImageSequence.Iterator(im):
        frames.append(f.convert("RGB").crop((L, T, L + side, T + side)).resize((360, 360), Image.LANCZOS))
        durs.append(f.info.get("duration", 30))
    pal = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    out = os.path.join(OUT, f"SimpleDodge-top-{d}.gif")
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durs, loop=0, optimize=True, disposal=1)
    print(d, (L, T, side), os.path.getsize(out) // 1024, "KB")
