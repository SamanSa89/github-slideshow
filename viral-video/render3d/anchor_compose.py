"""Animated 2D anchor (from a single portrait) over the 3D studio background + news overlays.

usage: python3 anchor_compose.py anchor.png mask.png bgframes workdir out.mp4 [still_frame_index]
- Lip sync: jaw/lower-lip warp + painted mouth interior driven by voice level
- Blink, brow raise on highlighted words, head tilt/nod, breathing
- Camera: smooth wide <-> close-up per scene with parallax against the background
"""
import json, math, subprocess, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

A_PNG, M_PNG, BGF, WORK, OUT = sys.argv[1:6]
STILL = int(sys.argv[6]) if len(sys.argv) > 6 else None
TL = json.load(open(f"{WORK}/timeline.json"))
W, H, FPS = 1080, 1920, TL["fps"]
NF = int(TL["total"] * FPS)

# ------------------------------------------------------------------ anchor setup (original image coordinates)
img = cv2.cvtColor(cv2.imread(A_PNG), cv2.COLOR_BGR2RGB)
mask = cv2.imread(M_PNG, 0)
ys_, xs_ = np.where(mask > 20)
BX0, BX1, BY0, BY1 = xs_.min() - 4, xs_.max() + 4, max(0, ys_.min() - 4), img.shape[0]
PERSON = np.dstack([img, mask])[BY0:BY1, BX0:BX1].copy()          # RGBA crop
FACE = (1305 - BX0, 520 - BY0)                                     # face anchor point in crop
MOUTH_X, LIP_Y = 1305 - BX0, 632 - BY0
EYES = [(1211 - BX0, 441 - BY0), (1396 - BX0, 441 - BY0)]
BROWS = [(1210 - BX0, 385 - BY0), (1400 - BX0, 385 - BY0)]
PIVOT = (1305 - BX0, 835 - BY0)
# head patch
HX0, HX1, HY0, HY1 = 760 - BX0, 1860 - BX0, 0, 920 - BY0
HX0 = max(HX0, 0); HX1 = min(HX1, PERSON.shape[1])
gy, gx = np.mgrid[HY0:HY1, HX0:HX1].astype(np.float32)

# closed-eye patches: vertical skin gradient + lash line
def closed_eye(cx, cy):
    rx, ry = 50, 27
    x0, x1, y0, y1 = cx - rx, cx + rx, cy - ry, cy + ry
    top = PERSON[y0 - 3, x0:x1, :3].astype(np.float32); bot = PERSON[y1 + 3, x0:x1, :3].astype(np.float32)
    k = np.linspace(0, 1, y1 - y0)[:, None, None]
    patch = top[None] * (1 - k) + bot[None] * k
    patch = cv2.GaussianBlur(patch, (0, 0), 2)
    xx = np.arange(x1 - x0) - rx
    lash = (cy + 3 - y0 + 6 * (1 - (xx / rx) ** 2)).astype(int)
    for i, ly in enumerate(lash):
        if abs(xx[i]) < rx * 0.92:
            patch[max(0, ly - 2):ly + 2, i] = patch[max(0, ly - 2):ly + 2, i] * 0.35 + np.array([40, 25, 20]) * 0.65
    m = np.zeros((y1 - y0, x1 - x0), np.float32)
    cv2.ellipse(m, (rx, ry), (rx - 6, ry - 5), 0, 0, 360, 1, -1)
    m = cv2.GaussianBlur(m, (0, 0), 3)
    return (x0, y0, patch, m)
CLOSED = [closed_eye(*e) for e in EYES]

def animate_head(a, blink, brow, theta, nod):
    patch = PERSON[HY0:HY1, HX0:HX1].astype(np.float32)
    X, Y = gx, gy
    # 1) jaw/lip + brow warp
    d = a * 26.0
    wx = np.exp(-((X - MOUTH_X) / 78.0) ** 2)
    wy = np.clip((Y - LIP_Y) / 4.0, 0, 1) * np.clip((870 - BY0 - Y) / 90.0, 0, 1)
    mapy = Y - d * wx * wy
    bw = sum(np.exp(-((X - bx) / 75.0) ** 2 - ((Y - by) / 30.0) ** 2) for bx, by in BROWS)
    mapy = mapy + brow * 7.0 * bw
    p1 = cv2.remap(patch, (X - HX0).astype(np.float32), (mapy - HY0).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    # 2) mouth interior
    if d > 1.0:
        g = np.zeros(p1.shape[:2], np.float32); col = np.zeros(p1.shape[:2] + (3,), np.float32)
        xs = np.arange(MOUTH_X - 60, MOUTH_X + 61)
        for x in xs:
            sh = max(0.0, 1 - ((x - MOUTH_X) / 60.0) ** 2) ** 0.7
            gap = d * math.exp(-((x - MOUTH_X) / 78.0) ** 2) * sh
            if gap < 0.8: continue
            y0 = LIP_Y - 1; y1 = int(LIP_Y + gap)
            g[y0 - HY0:y1 - HY0 + 1, x - HX0] = 1
        g = cv2.GaussianBlur(g, (0, 0), 1.6)
        yy = (Y - LIP_Y) / max(d, 1)
        base = np.stack([62 + 60 * yy, 16 + 22 * yy, 20 + 22 * yy], -1)
        if d > 13:  # lower teeth hint
            lt = np.exp(-((Y - (LIP_Y + d * 0.82)) / 2.2) ** 2) * np.exp(-((X - MOUTH_X) / 45.0) ** 2) * 0.55
            base = base * (1 - lt[..., None]) + np.array([225, 220, 214]) * lt[..., None]
        p1[..., :3] = p1[..., :3] * (1 - g[..., None]) + base * g[..., None]
    # 3) blink
    if blink > 0.01:
        for (x0, y0, cp, m) in CLOSED:
            hh, ww = m.shape; sy, sx = y0 - HY0, x0 - HX0
            al = (m * blink)[..., None]
            p1[sy:sy + hh, sx:sx + ww, :3] = p1[sy:sy + hh, sx:sx + ww, :3] * (1 - al) + cp * al
    # 4) head rotation + nod (weighted so the neck/shoulders stay put)
    w = np.clip((PIVOT[1] - 60 - Y) / 70.0 + 1, 0, 1)
    th = np.deg2rad(theta) * w
    dx, dy = X - PIVOT[0], Y - PIVOT[1]
    sx = PIVOT[0] + dx * np.cos(-th) - dy * np.sin(-th)
    sy = PIVOT[1] + dx * np.sin(-th) + dy * np.cos(-th) - nod * w
    p2 = cv2.remap(p1, (sx - HX0).astype(np.float32), (sy - HY0).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    out = PERSON.copy()
    out[HY0:HY1, HX0:HX1] = np.clip(p2, 0, 255).astype(np.uint8)
    return out

# ------------------------------------------------------------------ timing helpers
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
ease = lambda x: 1 - (1 - clamp(x)) ** 3
eio = lambda x: (lambda x: 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2)(clamp(x))
SCN = TL["scenes"]
def scene_at(t):
    cur = SCN[0]
    for s in SCN:
        if t >= s["start"] - 0.05: cur = s
    return cur
HLT = [w["t0"] for w in TL["words"] if w["hl"]]
def close_target(t):
    s = scene_at(t); k = (t - s["start"]) / max(0.1, s["end"] - s["start"])
    if s["name"] == "hook": return 1.0 if k < 0.62 else 0.0
    if s["name"] == "cta": return 1.0
    if s["name"] == "verdict": return 1.0 if k > 0.35 else 0.0
    return 0.0 if k < 0.55 else 1.0
# smooth closeness by integrating toward target (precompute)
CL = np.zeros(NF + 1); c = 1.0
for i in range(NF + 1):
    tgt = close_target(i / FPS); c += (tgt - c) * 0.075; CL[i] = c
CL = np.array([eio(x) for x in CL])
mouth = np.array(TL["mouth"] + [0] * 10)
blinks = []; tb = 1.3; rs = np.random.default_rng(5)
while tb < TL["total"]: blinks.append(tb); tb += rs.uniform(2.4, 5.2)
def blink_at(t):
    for b in blinks:
        if 0 <= t - b < 0.2: x = (t - b) / 0.2; return 1 - abs(2 * x - 1) ** 1.5
    return 0.0
def pulse(t, t0, up=0.2, hold=0.5, down=0.5):
    if t < t0: return 0.0
    if t < t0 + up: return eio((t - t0) / up)
    if t < t0 + up + hold: return 1.0
    return 1 - eio((t - t0 - up - hold) / down)

# ------------------------------------------------------------------ overlays (same look as compose.py)
FD = "/usr/share/fonts/truetype/dejavu/"; _fc = {}
def font(s, b=True):
    if (s, b) not in _fc: _fc[(s, b)] = ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if b else "DejaVuSans.ttf"), s)
    return _fc[(s, b)]
RED, WHITE, YEL, GREY = (220, 22, 42), (248, 248, 248), (255, 214, 60), (190, 198, 220)
def wt(scene, tok):
    for w in TL["words"]:
        if w["scene"] == scene and tok.lower() in w["w"].lower(): return w["t0"]
    return next(s["start"] for s in SCN if s["name"] == scene)
CHY = {
 "hook": [("DER DECODER", "WEM GEHÖRT DER HIMMEL?", None)],
 "starship": [("TEXAS · 14.11.2026", "SPACEX FÄNGT STARSHIP AUS DEM ORBIT", None), ("SPACEX", "+26 STARLINK-SATELLITEN AUSGESETZT", wt("starship", "26"))],
 "vulcan": [("FLORIDA · 15.11.2026", "ULA VULCAN STARTET FÜR AMAZON LEO", None), ("ANOMALIE NACH ~10 MIN", "40 VON 40 SATELLITEN VERLOREN", TL["events"]["anomaly"]),
            ("AMAZON LEO", "398 IM ORBIT · 3.236 BENÖTIGT", wt("vulcan", "400"))],
 "connect": [("ANALYSE", "SATELLITEN = INTERNET = MACHT", None), ("UKRAINE", "STARLINK SCHALTET AB 161 KM/H AB", wt("connect", "161"))],
 "genf": [("GENF · HEUTE", "128 STAATEN VERHANDELN ÜBER KILLERROBOTER", None), ("BERICHTE · UNBESTÄTIGT", "USA & RUSSLAND GEGEN MENSCHLICHE KONTROLLE?", wt("genf", "Berichten"))],
 "verdict": [("FAZIT", "PHYSIK + GELD = KONTROLLE", None)],
 "cta": [("PRÜF MICH", "QUELLEN IN DER BESCHREIBUNG", None)],
}
def chyron(d, t, s):
    items = [(k, h, a if a is not None else s["start"] + 0.4) for k, h, a in CHY.get(s["name"], [])]
    items = [i for i in items if t >= i[2]]
    if not items: return
    k, h, a = items[-1]; lt = t - a; out = s["end"] + 0.3 - t
    p = ease(lt / 0.45) * (ease(out / 0.35) if out < 0.35 else 1)
    if p <= 0: return
    y = 1700; x0 = 40; fk, fh = font(30), font(46)
    hw = d.textlength(h, font=fh)
    if hw > W - 120: fh = font(int(46 * (W - 120) / hw)); hw = d.textlength(h, font=fh)
    kw = d.textlength(k, font=fk); kc = YEL if "UNBEST" in k else RED
    d.rectangle([x0, y + 50, x0 + int((hw + 60) * p), y + 128], fill=(255, 255, 255, 240))
    d.rectangle([x0, y + 50, x0 + 8, y + 128], fill=RED)
    d.rectangle([x0, y, x0 + int((kw + 36) * p), y + 50], fill=kc + (255,))
    if p > 0.6:
        a_ = int(255 * clamp((p - 0.6) / 0.4))
        d.text((x0 + 18, y + 8), k, font=fk, fill=(0, 0, 0, a_) if kc == YEL else (255, 255, 255, a_))
        d.text((x0 + 30, y + 64), h, font=fh, fill=(10, 20, 60, a_))
GROUPS, cur = [], []
for w in TL["words"]:
    if cur and (len(cur) >= 4 or cur[-1]["scene"] != w["scene"] or cur[-1]["w"][-1] in ".?!:" or w["t0"] - cur[-1]["t1"] > 0.6):
        GROUPS.append(cur); cur = []
    cur.append(w)
GROUPS.append(cur)
def captions(d, t):
    for g in GROUPS:
        if g[0]["t0"] - 0.05 <= t < g[-1]["t1"] + 0.25:
            f = font(64); sp = d.textlength(" ", font=f)
            tot = sum(d.textlength(w["w"], font=f) for w in g) + sp * (len(g) - 1)
            if tot > W - 120: f = font(int(64 * (W - 120) / tot)); sp = d.textlength(" ", font=f); tot = sum(d.textlength(w["w"], font=f) for w in g) + sp * (len(g) - 1)
            x = (W - tot) / 2; y = 1560
            for w in g:
                col = RED if w["hl"] else (YEL if w["t0"] <= t < w["t1"] + 0.05 else WHITE)
                d.text((x, y), w["w"], font=f, fill=col, stroke_width=5, stroke_fill=(0, 0, 0)); x += d.textlength(w["w"], font=f) + sp
            return
TOPBAR = Image.new("RGBA", (W, 96)); td = ImageDraw.Draw(TOPBAR)
td.rectangle([0, 0, W, 96], fill=(4, 14, 48, 200)); td.rectangle([0, 92, W, 96], fill=RED)
td.text((80, 24), "DER DECODER", font=font(40), fill=WHITE)
lab = "KI-GENERIERT"; td.text((W - 40 - td.textlength(lab, font=font(28, False)), 32), lab, font=font(28, False), fill=GREY)

# ------------------------------------------------------------------ frame loop
ff = None
if STILL is None:
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-i", f"{WORK}/mix.wav", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", OUT], stdin=subprocess.PIPE)
lastbg = None; msm = 0.0
for fi in ([STILL] if STILL is not None else range(NF)):
    t = fi / FPS; s = scene_at(t); c = float(CL[fi])
    # --- anchor animation params
    lv = float(mouth[fi]); msm = 0.55 * msm + 0.45 * lv
    a = clamp(msm * 1.15) ** 0.85
    hl = max([pulse(t, h - 0.12) for h in HLT if -0.2 < t - h < 1.5] + [0])
    q = any(w["t0"] <= t < w["t1"] + 0.4 and w["w"].endswith("?") for w in TL["words"])
    theta = 1.1 * math.sin(t * 0.55) + 0.5 * math.sin(t * 1.37 + 1) + (1.6 if q else 0) * 1.0
    nod = 3.5 * msm + 2.0 * math.sin(t * 2.1) * msm + hl * 3
    person = animate_head(a, blink_at(t), hl, theta, nod)
    # --- camera framing
    sc = 0.668 + (1.02 - 0.668) * c
    breath = 1 + 0.004 * math.sin(t * 1.5)
    sway = 10 * math.sin(t * 0.31) * (1 - 0.4 * c)
    ph, pw = person.shape[:2]
    tw, th_ = int(pw * sc), int(ph * sc * breath)
    pr = cv2.resize(person, (tw, th_), interpolation=cv2.INTER_AREA)
    px = int(540 + sway - FACE[0] * sc); py = H - th_ + int(6 * c)
    # --- background with zoom/parallax + DOF
    try:
        bg = Image.open(f"{BGF}/f{fi:05d}.jpg").convert("RGB"); lastbg = bg
    except FileNotFoundError:
        bg = lastbg if lastbg is not None else Image.new("RGB", (720, 1280), (6, 20, 60))
    z = 1.04 + 0.16 * c
    bw_, bh_ = int(W * z), int(H * z)
    bgr = np.asarray(bg.resize((bw_, bh_), Image.BILINEAR))
    ox = int(min(max((bw_ - W) / 2 - sway * 0.35, 0), bw_ - W)); oy = int((bh_ - H) * 0.35)
    frame = bgr[oy:oy + H, ox:ox + W].astype(np.float32)
    if c > 0.05: frame = cv2.GaussianBlur(frame, (0, 0), 0.5 + 2.2 * c)
    # --- composite person
    x0, y0 = max(px, 0), max(py, 0); x1, y1 = min(px + tw, W), min(py + th_, H)
    sub = pr[y0 - py:y1 - py, x0 - px:x1 - px].astype(np.float32)
    al = sub[..., 3:4] / 255.0
    frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - al) + sub[..., :3] * al
    # subtle vignette
    img_o = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))
    ov = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(ov)
    for i in range(0, 420, 10): d.rectangle([0, H - 420 + i, W, H - 410 + i], fill=(0, 0, 20, int(120 * i / 420)))
    ov.alpha_composite(TOPBAR)
    if int(t * 1.6) % 2 == 0: d.ellipse([36, 34, 60, 58], fill=RED)
    chyron(d, t, s); captions(d, t)
    d.rectangle([0, H - 8, int(W * t / TL["total"]), H], fill=RED)
    out = Image.alpha_composite(img_o.convert("RGBA"), ov).convert("RGB")
    if STILL is not None: out.save(OUT); break
    ff.stdin.write(out.tobytes())
if ff: ff.stdin.close(); ff.wait()
print("done", OUT)
