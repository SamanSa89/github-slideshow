"""YouTube banner v2 for "The Decoder": no face (the profile picture carries the face), message-first.
2560x1440; headline + note inside the 1546x423 all-device safe area.

usage: python3 make_banner_v2.py map.jpg Caveat-Bold.ttf outdir
"""
import math, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

MAP, CAVEAT, OUT = sys.argv[1:4]
W, H = 2560, 1440
SAFE = (507, 508, 2053, 931)
FD = "/usr/share/fonts/truetype/dejavu/"
F = lambda s, b=True: ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if b else "DejaVuSans.ttf"), s)
CV = lambda s: ImageFont.truetype(CAVEAT, s)
RED, NAVY, WHITE, YEL, CHALK = (212, 20, 42), (6, 18, 52), (255, 255, 255), (255, 210, 60), (225, 235, 255)

# ---------------------------------------------------------------- background
y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
r = 4 + 10 * (1 - y) + 6 * x; g = 16 + 34 * (1 - y) + 8 * x; b = 50 + 105 * (1 - y) * (0.6 + 0.4 * x)
bg = Image.fromarray(np.dstack([np.broadcast_to(c, (H, W)) for c in (r, g, b)]).clip(0, 255).astype(np.uint8)).convert("RGBA")
d = ImageDraw.Draw(bg, "RGBA")
for gx in range(0, W, 80): d.line([gx, 0, gx, H], fill=(120, 170, 255, 6))
for gy in range(0, H, 80): d.line([0, gy, W, gy], fill=(120, 170, 255, 6))
mp = Image.open(MAP).convert("RGB").resize((1500, 1300))
fade = (np.ones((1300, 1500)) * np.clip(np.linspace(-0.2, 1.2, 1500), 0, 1)[None, :] * 115).astype(np.uint8)
bg.paste(mp, (1100, 100), Image.fromarray(fade).filter(ImageFilter.GaussianBlur(6)))
streaks = Image.new("RGBA", (W, H)); sd = ImageDraw.Draw(streaks)
for (x0, col, w_) in [(-500, (212, 20, 42, 60), 120), (60, (90, 160, 255, 45), 60), (2050, (212, 20, 42, 40), 90)]:
    sd.polygon([(x0, H), (x0 + w_, H), (x0 + w_ + 900, 0), (x0 + 900, 0)], fill=col)
bg = Image.alpha_composite(bg, streaks.filter(ImageFilter.GaussianBlur(28)))

# ---------------------------------------------------------------- chalk/marker doodles (Leinwand identity), mostly outside the text
dl = Image.new("RGBA", (W, H)); dd = ImageDraw.Draw(dl)
def dashed(pts, col, w=6, dash=26, gap=18):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        L = math.hypot(x2 - x1, y2 - y1); n = int(L // (dash + gap)) + 1
        for i in range(n):
            a = i * (dash + gap) / L; e = min(1, (i * (dash + gap) + dash) / L)
            dd.line([x1 + (x2 - x1) * a, y1 + (y2 - y1) * a, x1 + (x2 - x1) * e, y1 + (y2 - y1) * e], fill=col, width=w)
route = [(1880, 230), (1760, 300), (1640, 420), (1600, 560), (1520, 700), (1560, 860), (1800, 960), (2150, 990)]
pts = []
for (x1, y1), (x2, y2) in zip(route, route[1:]):
    for k in range(12): t = k / 12; pts.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t + math.sin(t * math.pi) * 12))
pts.append(route[-1]); dashed(pts, (232, 40, 52, 200))
dd.polygon([(2150, 990), (2112, 968), (2118, 1012)], fill=(232, 40, 52, 220))
for (px, py) in [(1640, 420), (1520, 700)]: dd.ellipse([px - 12, py - 12, px + 12, py + 12], fill=(232, 40, 52, 230))
dd.text((2170, 975), "Pacific", font=CV(54), fill=CHALK + (200,))
# magnifier (top-left, desktop area) + question marks + checkmark
dd.ellipse([180, 200, 380, 400], outline=CHALK + (120,), width=9); dd.line([360, 380, 460, 480], fill=CHALK + (120,), width=16)
dd.text((250, 245), "?", font=CV(120), fill=YEL + (150,))
dd.line([300, 1040, 340, 1090, 430, 980], fill=(80, 200, 120, 150), width=12)
dd.text((90, 610), "check the sources", font=CV(58), fill=CHALK + (110,))
bg = Image.alpha_composite(bg, dl)

# ---------------------------------------------------------------- headline (safe area)
d = ImageDraw.Draw(bg, "RGBA")
X = 600
d.rectangle([X, 528, X + 330, 586], fill=RED); d.text((X + 18, 535), "● LIVE NEWS", font=F(38), fill=WHITE)
d.text((X + 352, 537), "FACT-CHECKED · GLOBAL", font=F(36, False), fill=(215, 225, 250))
d.text((X - 4, 610), "BREAKING NEWS.", font=F(86), fill=WHITE)
bar = [(X - 18, 728), (X + 730, 728), (X + 702, 856), (X - 46, 856)]
d.polygon([(px + 10, py + 12) for px, py in bar], fill=(0, 0, 0, 110)); d.polygon(bar, fill=RED)
d.text((X + 6, 726), "DECODED.", font=F(120), fill=WHITE)
d.text((X, 878), "QUESTION  ·  VERIFY  ·  DECODE", font=F(40), fill=(220, 230, 252))

# ---------------------------------------------------------------- whiteboard note (inside the safe area, right)
card = Image.new("RGBA", (520, 360)); cd = ImageDraw.Draw(card)
cd.rounded_rectangle([10, 10, 510, 350], 16, fill=(250, 246, 236, 255), outline=(43, 47, 58, 255), width=9)
cd.text((260, 82), "Don't trust me.", font=CV(62), fill=(29, 36, 51), anchor="mm")
cd.rounded_rectangle([58, 140, 462, 262], 34, fill=(255, 210, 60, 170))
cd.text((260, 200), "VERIFY ME!", font=CV(92), fill=RED, anchor="mm")
cd.ellipse([36, 128, 484, 274], outline=RED, width=6)
cd.text((260, 312), "– The Decoder", font=CV(44), fill=(31, 95, 191), anchor="mm")
card = card.rotate(-4, expand=True, resample=Image.BICUBIC)
card = card.resize((int(card.width * 0.86), int(card.height * 0.86)), Image.LANCZOS)
cx, cy = 2048 - card.width, 548
cs = Image.new("RGBA", (W, H)); cs.paste((0, 0, 0, 130), (cx + 16, cy + 20), card.split()[3])
bg = Image.alpha_composite(bg, cs.filter(ImageFilter.GaussianBlur(14))); bg.alpha_composite(card, (cx, cy))

# ---------------------------------------------------------------- desk bar + ticker (TV/desktop)
d = ImageDraw.Draw(bg, "RGBA")
d.rectangle([0, 1218, W, H], fill=NAVY + (255,)); d.rectangle([0, 1210, W, 1218], fill=RED); d.rectangle([0, 0, W, 10], fill=RED)
tick = "THE DECODER   •   BREAKING NEWS   •   GLOBAL NEWS, DECODED   •   VERIFY ME   •   "
tx = 30
while tx < W: d.text((tx, 1262), tick, font=F(44), fill=(220, 228, 250)); tx += d.textlength(tick, font=F(44))

out = bg.convert("RGB")
out.save(f"{OUT}/youtube-banner-v2-2560x1440.png", optimize=True)
out.save(f"{OUT}/youtube-banner-v2-2560x1440.jpg", quality=92)
pv = out.copy(); pd = ImageDraw.Draw(pv)
pd.rectangle(SAFE, outline=(0, 255, 120), width=6); pd.text((SAFE[0] + 10, SAFE[3] + 8), "safe area (all devices)", font=F(34), fill=(0, 255, 120))
pd.rectangle([0, 509, W, 931], outline=(255, 230, 0), width=3)
pv.resize((1280, 720), Image.LANCZOS).save(f"{OUT}/banner-v2-preview-guides.jpg", quality=90)
print("ok")
