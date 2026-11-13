# make_page_gifs_120.py - the 1.2.0 Nexus page GIFs (2026-11-13; the owner: "we need to swap in the new, more accurate
# GIFs that describe what each motion does"). Same style as make_page_gifs.py (showcase_render.py --follow frames:
# top-down, riding the character, vanilla Steel armour; 400x400, looping, a half-second hold at the end), plus a label
# burned in along the bottom in the page cards' look (card.html: dark band, serif capitals, gold accent #e8c766).
#   gif-showcase\page-1.2.0\SimpleDodge-step-<Dir>.gif   the eight grounded steps   (StepDodge<Dir>.blend)
#   gif-showcase\page-1.2.0\SimpleDodge-roll-<Dir>.gif   the eight directional rolls (rolls\Roll<Dir>.blend)
#   gif-showcase\page-1.2.0\SimpleDodge-chain.gif        step > short roll > long roll, forward, one continuous floor
#                                                         (showcase_render.py --follow --chain Forward RollForward
#                                                         LongRollForward; the active stage of the label lights up)
# The 1.1.0 GIFs in gif-showcase\page\ are left as they are.
# Run (after the renders): py -3 make_page_gifs_120.py
import glob, os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_showcase_follow"); OUT = os.path.join(HERE, "gif-showcase", "page-1.2.0")
os.makedirs(OUT, exist_ok=True)
DIRS = ("Forward", "Back", "Left", "Right", "ForwardLeft", "ForwardRight", "BackLeft", "BackRight")
WORDS = {"Forward": "forward", "Back": "back", "Left": "left", "Right": "right", "ForwardLeft": "forward left",
         "ForwardRight": "forward right", "BackLeft": "back left", "BackRight": "back right"}
SIZE = 400
GOLD, IVORY, DIM, BAND = (232, 199, 102), (239, 233, 220), (142, 139, 132), (5, 5, 5)
# card.html sets Cinzel with Georgia as its fallback; Cinzel is not installed here, so Georgia Bold in capitals
GEORGIA_B = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "georgiab.ttf")
FONT = ImageFont.truetype(GEORGIA_B, 17)
FONT_CHAIN = ImageFont.truetype(GEORGIA_B, 15)   # the three-stage label is longer
TRACK = 2          # letter spacing, px (the cards' titles are tracked)
BAND_H = 40


def tracked_width(d, s, font):
    return sum(d.textlength(c, font=font) + TRACK for c in s) - TRACK


def label(im, parts, font=FONT):
    """parts: [(text, colour), ...] drawn centred in a dark band along the bottom, a gold hairline above it."""
    im = im.convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    y0 = SIZE - BAND_H
    d.rectangle((0, y0, SIZE, SIZE), fill=BAND + (220,))
    d.line((0, y0, SIZE, y0), fill=GOLD + (255,), width=1)
    total = sum(tracked_width(d, t, font) for t, _ in parts) + TRACK * (len(parts) - 1)
    x = (SIZE - total) / 2; asc, desc = font.getmetrics(); y = y0 + (BAND_H - asc) / 2 + 1
    for t, col in parts:
        for c in t:
            d.text((x, y), c, font=font, fill=col + (255,)); x += d.textlength(c, font=font) + TRACK
        x += TRACK
    return Image.alpha_composite(im, ov).convert("RGB")


def frames(d):
    pngs = sorted(glob.glob(os.path.join(SRC, d, "[0-9][0-9][0-9].png")))
    if not pngs: raise SystemExit(f"no frames in {os.path.join(SRC, d)} - run showcase_render.py --follow first")
    return [Image.open(p).convert("RGB").resize((SIZE, SIZE), Image.LANCZOS) for p in pngs]


def save(fr, name, colors=128):
    # one palette for the whole GIF, taken from a strip of its frames: per-frame palettes lost the thin gold text and
    # made the floor shimmer from frame to frame
    step = max(1, len(fr) // 8); sample = fr[::step]
    strip = Image.new("RGB", (SIZE, SIZE * len(sample) + 120))
    for i, f in enumerate(sample): strip.paste(f, (0, i * SIZE))
    # the label's own colours as solid blocks, so the palette keeps them apart (without these, the few ivory pixels
    # were merged into the gold and "STEP - LEFT" came out all gold)
    for i, col in enumerate((GOLD, IVORY, DIM)):
        strip.paste(col, (i * SIZE // 3, SIZE * len(sample), (i + 1) * SIZE // 3, SIZE * len(sample) + 120))
    pal = strip.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in fr]
    durs = [33] * len(q); durs[-1] = 500
    out = os.path.join(OUT, name)
    q[0].save(out, save_all=True, append_images=q[1:], duration=durs, loop=0, optimize=True)
    print(name, len(q), "frames", round(os.path.getsize(out) / 1024), "KB")
    return out


for d in DIRS:
    save([label(f, [("STEP - ", GOLD), (WORDS[d].upper(), IVORY)]) for f in frames(d)], f"SimpleDodge-step-{d}.gif")
    save([label(f, [("ROLL - ", GOLD), (WORDS[d].upper(), IVORY)]) for f in frames("Roll" + d)], f"SimpleDodge-roll-{d}.gif")

# the chain: each clip's first frame is the stance the one before ended on, so it is dropped after the first clip
stages = [("Chain1_Forward", "STEP"), ("Chain2_RollForward", "SHORT ROLL"), ("Chain3_LongRollForward", "LONG ROLL")]
chain = []
for i, (d, _) in enumerate(stages):
    parts = []
    for j, (_, word) in enumerate(stages):
        parts.append((word, GOLD if j == i else DIM))
        if j < len(stages) - 1: parts.append((" > ", DIM))
    fr = frames(d)
    chain += [label(f, parts, FONT_CHAIN) for f in (fr if i == 0 else fr[1:])]
save(chain, "SimpleDodge-chain.gif")
