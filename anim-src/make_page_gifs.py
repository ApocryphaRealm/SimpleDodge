# make_page_gifs.py - the Nexus page GIFs: showcase_render.py --follow frames (top-down, riding the character) ->
# gif-showcase\page\SimpleDodge-top-<Dir>.gif, 400x400, looping, with a half-second hold on the stance at the end.
# Run: py -3 make_page_gifs.py
import glob, os
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_showcase_follow"); OUT = os.path.join(HERE, "gif-showcase", "page"); os.makedirs(OUT, exist_ok=True)
for d in ("Forward", "Back", "Left", "Right", "ForwardLeft", "ForwardRight", "BackLeft", "BackRight"):
    pngs = sorted(glob.glob(os.path.join(SRC, d, "[0-9][0-9][0-9].png")))
    fr = [Image.open(p).convert("RGB").resize((400, 400), Image.LANCZOS) for p in pngs]
    pal = [f.quantize(colors=160, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in fr]
    durs = [33] * len(pal); durs[-1] = 500
    out = os.path.join(OUT, f"SimpleDodge-top-{d}.gif")
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durs, loop=0, optimize=True)
    print(d, len(pal), "frames", os.path.getsize(out) // 1024, "KB")
