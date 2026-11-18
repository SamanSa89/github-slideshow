"""YouTube profile picture for "The Decoder" (800x800, designed for the round crop shown at 98px).

usage: python3 make_avatar.py anchor.png mask.png outdir
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

A, MASK, OUT = sys.argv[1:4]
S = 800
FD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
RED, WHITE = (212, 20, 42), (255, 255, 255)

# background: studio blue radial gradient
yy, xx = np.mgrid[0:S, 0:S] / S
rr = np.sqrt((xx - 0.5) ** 2 + (yy - 0.42) ** 2)
k = np.clip(1 - rr * 1.6, 0, 1)
bg = np.dstack([8 + 30 * k, 26 + 80 * k, 70 + 150 * k]).astype(np.uint8)
img = Image.fromarray(bg).convert("RGBA")

# anchor: head & shoulders, face slightly above centre (round crop keeps it)
an = Image.open(A).convert("RGB"); m = Image.open(MASK).convert("L")
s = 0.82; face = (1305, 470); target = (400, 360)
an = an.resize((int(an.width * s), int(an.height * s)), Image.LANCZOS); m = m.resize(an.size, Image.LANCZOS)
ox, oy = int(target[0] - face[0] * s), int(target[1] - face[1] * s)
rim = Image.new("RGBA", (S, S)); rim.paste((120, 180, 255, 140), (ox, oy - 4), m.filter(ImageFilter.MaxFilter(11)))
img = Image.alpha_composite(img, rim.filter(ImageFilter.GaussianBlur(10)))
img.paste(an, (ox, oy), m)

# red ring + "THE DECODER" band at the bottom (inside the circle)
d = ImageDraw.Draw(img, "RGBA")
d.rectangle([0, 600, S, 690], fill=RED + (240,))
f = ImageFont.truetype(FD, 64)
d.text((S / 2, 646), "THE DECODER", font=f, fill=WHITE, anchor="mm")
ring = Image.new("L", (S, S), 0); ImageDraw.Draw(ring).ellipse([6, 6, S - 6, S - 6], outline=255, width=22)
img.paste(RED, (0, 0), ring)

img = img.convert("RGB")
img.save(f"{OUT}/youtube-profile-800x800.png", optimize=True)
# preview of the round crop at real display sizes
pv = Image.new("RGB", (560, 300), (24, 24, 28)); circ = Image.new("L", (S, S), 0); ImageDraw.Draw(circ).ellipse([0, 0, S, S], fill=255)
for i, sz in enumerate([240, 98, 48]):
    c = img.resize((sz, sz), Image.LANCZOS); mk = circ.resize((sz, sz), Image.LANCZOS)
    pv.paste(c, ([20, 300, 440][i], 150 - sz // 2), mk)
pv.save(f"{OUT}/profile-preview-round.jpg", quality=92)
print("ok")
