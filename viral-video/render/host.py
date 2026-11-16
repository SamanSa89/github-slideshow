"""Original cartoon host 'Der Decoder' – pre-rendered sprites (supersampled)."""
from PIL import Image, ImageDraw, ImageFilter
S = 2  # supersample
SKIN, SKIN_D, HAIR = (226, 176, 140), (196, 146, 112), (32, 26, 26)
SUIT, SUIT_D, SHIRT, TIE = (28, 38, 66), (18, 24, 44), (240, 240, 245), (205, 30, 45)

def _r(d, box, **k): d.rounded_rectangle([v * S for v in box], radius=k.pop("r", 0) * S, **k)
def _e(d, box, **k): d.ellipse([v * S for v in box], **k)
def _p(d, pts, **k): d.polygon([(x * S, y * S) for x, y in pts], **k)
def _l(d, pts, w, **k): d.line([(x * S, y * S) for x, y in pts], width=w * S, joint="curve", **k)

def body(w=820, h=520):
    im = Image.new("RGBA", (w * S, h * S)); d = ImageDraw.Draw(im)
    cx = w // 2
    _r(d, [cx - 70, 0, cx + 70, 130], fill=SKIN_D, r=30)                       # neck
    _p(d, [(cx - 330, 520), (cx - 300, 170), (cx - 160, 90), (cx + 160, 90), (cx + 300, 170), (cx + 330, 520)], fill=SUIT)
    _p(d, [(cx - 95, 85), (cx + 95, 85), (cx, 300)], fill=SHIRT)              # shirt V
    _p(d, [(cx - 25, 110), (cx + 25, 110), (cx + 40, 330), (cx, 380), (cx - 40, 330)], fill=TIE)
    _p(d, [(cx - 30, 85), (cx + 30, 85), (cx + 22, 118), (cx - 22, 118)], fill=(170, 20, 35))
    _p(d, [(cx - 160, 90), (cx - 95, 85), (cx, 300), (cx - 60, 420), (cx - 150, 220)], fill=SUIT_D)   # lapels
    _p(d, [(cx + 160, 90), (cx + 95, 85), (cx, 300), (cx + 60, 420), (cx + 150, 220)], fill=SUIT_D)
    _r(d, [cx + 150, 250, cx + 215, 262], fill=(230, 40, 50), r=4)            # red pocket square stripe
    _e(d, [cx - 210, 250, cx - 180, 280], fill=(230, 40, 50))                  # lapel pin
    return im.resize((w, h), Image.LANCZOS)

def head(mouth=0, blink=False, brow=0, w=560, h=640):
    im = Image.new("RGBA", (w * S, h * S)); d = ImageDraw.Draw(im)
    cx = w // 2
    _e(d, [cx - 210, 270, cx - 160, 380], fill=SKIN_D); _e(d, [cx + 160, 270, cx + 210, 380], fill=SKIN_D)   # ears
    # face: skull + jaw
    _e(d, [cx - 185, 100, cx + 185, 470], fill=SKIN)
    _e(d, [cx - 178, 180, cx + 178, 548], fill=SKIN)
    _p(d, [(cx - 184, 290), (cx - 150, 450), (cx - 60, 530), (cx + 60, 530), (cx + 150, 450), (cx + 184, 290)], fill=SKIN)
    # stubble
    st = Image.new("RGBA", im.size); sd = ImageDraw.Draw(st)
    _p(sd, [(cx - 175, 380), (cx - 145, 470), (cx - 60, 528), (cx + 60, 528), (cx + 145, 470), (cx + 175, 380), (cx + 120, 420), (cx, 430), (cx - 120, 420)], fill=(60, 45, 40, 38))
    im.alpha_composite(st.filter(ImageFilter.GaussianBlur(14 * S)))
    d = ImageDraw.Draw(im)
    # hair: top + quiff + sides
    _p(d, [(cx - 192, 280), (cx - 200, 180), (cx - 150, 95), (cx - 40, 55), (cx + 80, 45), (cx + 170, 85), (cx + 205, 170), (cx + 192, 280), (cx + 170, 200), (cx + 60, 150), (cx - 40, 175), (cx - 150, 190), (cx - 175, 240)], fill=HAIR)
    _p(d, [(cx - 60, 60), (cx + 40, 20), (cx + 150, 40), (cx + 110, 70)], fill=HAIR)    # quiff
    _l(d, [(cx - 20, 150), (cx + 100, 110)], 4, fill=(70, 60, 60))                    # hair highlight
    # brows
    ly = 225 - (0 if brow == 0 else 6); ry = 225 - (0 if brow == 0 else 26)
    _l(d, [(cx - 140, ly + 8), (cx - 95, ly - 6), (cx - 45, ly)], 16, fill=HAIR)
    _l(d, [(cx + 45, ry), (cx + 95, ry - 8), (cx + 140, ry + 4)], 16, fill=HAIR)
    # eyes
    for ex in (cx - 92, cx + 92):
        if blink:
            _l(d, [(ex - 36, 275), (ex, 282), (ex + 36, 275)], 7, fill=HAIR)
        else:
            _e(d, [ex - 40, 252, ex + 40, 298], fill=(250, 250, 250))
            _e(d, [ex - 20, 255, ex + 20, 295], fill=(70, 95, 130))
            _e(d, [ex - 10, 265, ex + 10, 285], fill=(15, 15, 20))
            _e(d, [ex + 4, 263, ex + 12, 271], fill=(255, 255, 255))
            _l(d, [(ex - 42, 258), (ex, 246), (ex + 42, 258)], 6, fill=HAIR)       # lid line
    # nose
    _l(d, [(cx + 8, 290), (cx + 18, 370), (cx - 12, 382)], 6, fill=SKIN_D)
    # mouth
    my = 445
    if mouth == 0:
        _l(d, [(cx - 60, my), (cx, my + 8), (cx + 55, my - 6), (cx + 70, my - 14)], 8, fill=(120, 50, 50))   # smirk
    else:
        hh = [0, 14, 26, 40, 54][mouth]; ww = [0, 52, 58, 62, 64][mouth]
        _e(d, [cx - ww, my - hh // 2, cx + ww, my + hh], fill=(70, 20, 25))
        _r(d, [cx - ww + 14, my - hh // 2 + 2, cx + ww - 14, my - hh // 2 + 12], fill=(245, 245, 245), r=4)
        if mouth >= 3: _e(d, [cx - 26, my + hh - 20, cx + 26, my + hh - 4], fill=(190, 80, 90))
    # headset mic
    _l(d, [(cx - 185, 330), (cx - 150, 420), (cx - 75, 455)], 6, fill=(20, 20, 25))
    _e(d, [cx - 90, 440, cx - 58, 470], fill=(20, 20, 25))
    return im.resize((w, h), Image.LANCZOS)

def sprites():
    return {(m, b, br): head(m, b, br) for m in range(5) for b in (False, True) for br in (0, 1)}
