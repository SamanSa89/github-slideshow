"""YouTube channel banner for "The Decoder" (2560x1440; text + face inside the 1546x423 all-device safe area).

usage: python3 make_banner.py anchor.png mask.png map.jpg Caveat-Bold.ttf outdir
"""
import math, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

A, MASK, MAP, CAVEAT, OUT = sys.argv[1:6]
W, H = 2560, 1440
SAFE = (507, 508, 2053, 931)                       # visible on every device
FD = "/usr/share/fonts/truetype/dejavu/"
F = lambda s, b=True: ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if b else "DejaVuSans.ttf"), s)
RED, NAVY, WHITE, YEL = (212, 20, 42), (6, 18, 52), (255, 255, 255), (255, 210, 60)

# ---------------------------------------------------------------- background: studio blue, grid, map, light streaks
y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
r = 4 + 10 * (1 - y) + 6 * x; g = 16 + 36 * (1 - y) + 10 * x; b = 52 + 110 * (1 - y) * (0.6 + 0.4 * x)
bg = Image.fromarray(np.dstack([np.broadcast_to(c, (H, W)) for c in (r, g, b)]).clip(0, 255).astype(np.uint8))
d = ImageDraw.Draw(bg, "RGBA")
for gx in range(0, W, 80): d.line([gx, 0, gx, H], fill=(120, 170, 255, 14), width=1)
for gy in range(0, H, 80): d.line([0, gy, W, gy], fill=(120, 170, 255, 14), width=1)
mp = Image.open(MAP).convert("RGB").resize((1100, 1110))
mp_a = Image.new("L", mp.size, 0); ImageDraw.Draw(mp_a).rectangle([0, 0, *mp.size], fill=150)
mp_a = Image.fromarray((np.asarray(mp_a) * np.linspace(0, 1, mp.size[0])[None, :] ** 0.7).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4))
bg.paste(mp, (1460, 180), mp_a)
streaks = Image.new("RGBA", (W, H)); sd = ImageDraw.Draw(streaks)
for (x0, col, w_) in [(-300, (212, 20, 42, 70), 120), (300, (90, 160, 255, 50), 60), (1950, (212, 20, 42, 45), 90), (2250, (90, 160, 255, 40), 50)]:
    sd.polygon([(x0, H), (x0 + w_, H), (x0 + w_ + 900, 0), (x0 + 900, 0)], fill=col)
bg = Image.alpha_composite(bg.convert("RGBA"), streaks.filter(ImageFilter.GaussianBlur(28)))
glow = Image.new("RGBA", (W, H)); ImageDraw.Draw(glow).ellipse([450, 360, 1170, 1080], fill=(80, 140, 255, 90))
bg = Image.alpha_composite(bg, glow.filter(ImageFilter.GaussianBlur(120)))

# ---------------------------------------------------------------- anchor (face inside safe area)
im = Image.open(A).convert("RGB"); m = Image.open(MASK).convert("L")
s = 0.47; face = (1305, 520); target = (820, 728)
im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS); m = m.resize(im.size, Image.LANCZOS)
ox, oy = int(target[0] - face[0] * s), int(target[1] - face[1] * s)
shadow = Image.new("RGBA", (W, H)); shadow.paste((0, 0, 20, 160), (ox + 18, oy + 22), m)
bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(24)))
rim = Image.new("RGBA", (W, H)); rim.paste((120, 180, 255, 120), (ox - 6, oy - 4), m.filter(ImageFilter.MaxFilter(9)))
bg = Image.alpha_composite(bg, rim.filter(ImageFilter.GaussianBlur(10)))
bg.paste(im, (ox, oy), m)

# ---------------------------------------------------------------- news desk bar + ticker (desktop/TV area)
d = ImageDraw.Draw(bg, "RGBA")
d.rectangle([0, 1218, W, H], fill=NAVY + (255,)); d.rectangle([0, 1210, W, 1218], fill=RED)
tick = "THE DECODER   •   BREAKING NEWS   •   GLOBAL NEWS, DECODED   •   VERIFY ME   •   "
tx = 30
while tx < W: d.text((tx, 1262), tick, font=F(44), fill=(220, 228, 250)); tx += d.textlength(tick, font=F(44))
d.rectangle([0, 0, W, 10], fill=RED)

# ---------------------------------------------------------------- title block (inside safe area)
X = 1160
d.rectangle([X, 528, X + 420, 588], fill=RED); d.text((X + 18, 536), "BREAKING NEWS", font=F(40), fill=WHITE)
d.ellipse([X + 440, 545, X + 466, 571], fill=RED)
d.text((X + 480, 538), "LIVE ANALYSIS", font=F(36, False), fill=(220, 228, 250))
d.text((X + 4, 606), "THE", font=F(78), fill=WHITE)
bar = [(X - 10, 702), (X + 880, 702), (X + 850, 852), (X - 40, 852)]
d.polygon([(px + 10, py + 12) for px, py in bar], fill=(0, 0, 0, 110)); d.polygon(bar, fill=RED)
d.text((X + 14, 700), "DECODER", font=F(150), fill=WHITE)
d.text((X + 6, 868), "QUESTION  ·  VERIFY  ·  DECODE", font=F(44), fill=(225, 232, 252))

# ---------------------------------------------------------------- whiteboard note (desktop accent, like the Leinwand)
card = Image.new("RGBA", (470, 300)); cd = ImageDraw.Draw(card)
cd.rounded_rectangle([10, 10, 460, 290], 14, fill=(250, 246, 236, 255), outline=(43, 47, 58, 255), width=8)
cv = ImageFont.truetype(CAVEAT, 78); cv2 = ImageFont.truetype(CAVEAT, 54)
cd.text((235, 70), "Don't trust me.", font=cv2, fill=(29, 36, 51), anchor="mm")
cd.rounded_rectangle([60, 120, 410, 230], 30, fill=(255, 210, 60, 170))
cd.text((235, 175), "VERIFY ME!", font=cv, fill=RED, anchor="mm")
cd.ellipse([38, 112, 432, 240], outline=RED, width=5)
card = card.rotate(4, expand=True, resample=Image.BICUBIC)
cs = Image.new("RGBA", (W, H)); cs.paste((0, 0, 0, 120), (2065 + 14, 590 + 18), card.split()[3])
bg = Image.alpha_composite(bg, cs.filter(ImageFilter.GaussianBlur(14)))
bg.alpha_composite(card, (2065, 590))

out = bg.convert("RGB")
out.save(f"{OUT}/youtube-banner-2560x1440.png", optimize=True)
out.save(f"{OUT}/youtube-banner-2560x1440.jpg", quality=92)
# preview with device-crop guides
pv = out.copy(); pd = ImageDraw.Draw(pv)
pd.rectangle(SAFE, outline=(0, 255, 120), width=6); pd.text((SAFE[0] + 10, SAFE[3] + 8), "safe area (all devices) 1546x423", font=F(34), fill=(0, 255, 120))
pd.rectangle([0, 509, W, 931], outline=(255, 230, 0), width=3); pd.text((20, 940), "mobile/desktop strip", font=F(30), fill=(255, 230, 0))
pd.rectangle([0, 0, W - 1, H - 1], outline=(255, 80, 80), width=6); pd.text((20, 20), "TV (full image)", font=F(30), fill=(255, 80, 80))
pv.resize((1280, 720), Image.LANCZOS).save(f"{OUT}/banner-preview-guides.jpg", quality=90)
print("ok")
