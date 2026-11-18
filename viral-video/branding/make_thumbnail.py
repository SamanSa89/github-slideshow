"""Thumbnails for the EN airspace episode: 1280x720 (landscape) and 1080x1920 (Shorts cover).

usage: python3 make_thumbnail.py anchor.png mask.png map.jpg Caveat-Bold.ttf outdir
"""
import math, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

A, MASK, MAP, CAVEAT, OUT = sys.argv[1:6]
FD = "/usr/share/fonts/truetype/dejavu/"
F = lambda s: ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", s)
CV = lambda s: ImageFont.truetype(CAVEAT, s)
RED, WHITE, YEL, NAVY = (212, 20, 42), (255, 255, 255), (255, 210, 60), (6, 18, 52)

def background(W, H):
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
    arr = np.dstack([np.broadcast_to(c, (H, W)) for c in (6 + 8 * x, 18 + 30 * (1 - y), 60 + 110 * (1 - y))]).clip(0, 255).astype(np.uint8)
    im = Image.fromarray(arr).convert("RGBA")
    mp = Image.open(MAP).convert("RGB").resize((int(W * 0.9), int(H * 0.9)))
    im.paste(mp, (int(W * 0.1), int(H * 0.05)), Image.new("L", mp.size, 70))
    return im

def jet(d, x, y, ang, sz, col):
    P = [[0, -1], [0.12, -0.55], [0.12, -0.15], [0.75, 0.25], [0.75, 0.38], [0.12, 0.2], [0.1, 0.62], [0.35, 0.8], [0.35, 0.9], [0, 0.82], [-0.35, 0.9], [-0.35, 0.8], [-0.1, 0.62], [-0.12, 0.2], [-0.75, 0.38], [-0.75, 0.25], [-0.12, -0.15], [-0.12, -0.55]]
    c, s = math.cos(ang + math.pi / 2), math.sin(ang + math.pi / 2)
    d.polygon([(x + (px * c - py * s) * sz, y + (px * s + py * c) * sz) for px, py in P], fill=col, outline=(80, 0, 0))

def anchor_layer(W, H, s, face_xy):
    im = Image.open(A).convert("RGB"); m = Image.open(MASK).convert("L")
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS); m = m.resize(im.size, Image.LANCZOS)
    ox, oy = int(face_xy[0] - 1305 * s), int(face_xy[1] - 520 * s)
    lay = Image.new("RGBA", (W, H)); rim = Image.new("RGBA", (W, H))
    rim.paste((255, 255, 255, 255), (ox, oy), m.filter(ImageFilter.MaxFilter(15)))
    lay.paste(im, (ox, oy), m)
    return rim.filter(ImageFilter.GaussianBlur(2)), lay

def outlined(d, xy, txt, f, fill, stroke=8, anchor="la"):
    d.text(xy, txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0), anchor=anchor)

# ---------------------------------------------------------------- 1280x720
W, H = 1280, 720
im = background(W, H)
rim, an = anchor_layer(W, H, 0.5, (1010, 330))
im = Image.alpha_composite(im, rim); im = Image.alpha_composite(im, an)
d = ImageDraw.Draw(im, "RGBA")
route = [(560, 70), (470, 170), (420, 300), (470, 420), (650, 470)]
for (x1, y1), (x2, y2) in zip(route, route[1:]):
    for k in range(0, 10, 2):
        t0, t1 = k / 10, (k + 1) / 10
        d.line([x1 + (x2 - x1) * t0, y1 + (y2 - y1) * t0, x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1], fill=(255, 70, 80), width=7)
jet(d, 520, 120, 2.3, 46, RED); jet(d, 600, 70, 2.3, 40, RED)
d.rectangle([40, 40, 330, 100], fill=RED); d.text((56, 48), "● BREAKING", font=F(40), fill=WHITE)
outlined(d, (40, 120), "4:07 AM", F(150), YEL, 10)
outlined(d, (40, 300), "RUSSIAN JETS", F(84), WHITE, 8)
outlined(d, (40, 395), "OVER JAPAN", F(84), WHITE, 8)
d.rounded_rectangle([40, 520, 600, 650], 18, fill=(250, 246, 236, 255), outline=(43, 47, 58), width=6)
d.text((320, 585), "…then they didn't turn back", font=CV(54), fill=RED, anchor="mm")
im.convert("RGB").save(f"{OUT}/thumbnail-airspace-en-1280x720.jpg", quality=92)

# ---------------------------------------------------------------- 1080x1920 Shorts cover
W, H = 1080, 1920
im = background(W, H)
rim, an = anchor_layer(W, H, 0.78, (540, 1300))
im = Image.alpha_composite(im, rim); im = Image.alpha_composite(im, an)
d = ImageDraw.Draw(im, "RGBA")
d.rectangle([0, 1760, W, H], fill=NAVY); d.rectangle([0, 1752, W, 1760], fill=RED)
d.text((W / 2, 1838), "THE DECODER  ·  VERIFY ME", font=F(52), fill=WHITE, anchor="mm")
d.rectangle([70, 150, 440, 225], fill=RED); d.text((92, 160), "● BREAKING", font=F(50), fill=WHITE)
outlined(d, (70, 250), "4:07 AM", F(210), YEL, 12)
outlined(d, (70, 490), "RUSSIAN JETS", F(118), WHITE, 10)
outlined(d, (70, 625), "OVER JAPAN", F(118), WHITE, 10)
jet(d, 860, 250, 2.3, 70, RED); jet(d, 960, 180, 2.3, 58, RED)
card = Image.new("RGBA", (760, 150)); cd = ImageDraw.Draw(card)
cd.rounded_rectangle([6, 6, 754, 144], 18, fill=(250, 246, 236, 255), outline=(43, 47, 58, 255), width=7)
cd.text((380, 75), "…and they didn't turn back", font=CV(70), fill=RED, anchor="mm")
card = card.rotate(-3, expand=True, resample=Image.BICUBIC); im.alpha_composite(card, (150, 790))
im.convert("RGB").save(f"{OUT}/shorts-cover-airspace-en-1080x1920.jpg", quality=92)
print("ok")
