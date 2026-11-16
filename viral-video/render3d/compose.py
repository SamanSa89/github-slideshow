"""Composite 3D frames + clean news overlays + captions, mux with audio.
usage: python3 compose.py framesdir workdir out.mp4
"""
import json, math, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

FR, WORK, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
TL = json.load(open(f"{WORK}/timeline.json"))
W, H, FPS = 1080, 1920, TL["fps"]
NF = int(TL["total"] * FPS)
FD = "/usr/share/fonts/truetype/dejavu/"
_fc = {}
def font(s, b=True):
    if (s, b) not in _fc: _fc[(s, b)] = ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if b else "DejaVuSans.ttf"), s)
    return _fc[(s, b)]
RED, WHITE, YEL, GREY = (232, 38, 52), (248, 248, 248), (255, 214, 60), (170, 172, 185)
clamp = lambda x, a=0, b=1: max(a, min(b, x))
ease = lambda x: 1 - (1 - clamp(x)) ** 3

def wt(scene, tok):
    for w in TL["words"]:
        if w["scene"] == scene and tok.lower() in w["w"].lower(): return w["t0"]
    return next(s["start"] for s in TL["scenes"] if s["name"] == scene)

# chyron: (scene, kicker, headline, appear-time)
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
SC = {s["name"]: s for s in TL["scenes"]}

def scene_at(t):
    cur = TL["scenes"][0]
    for s in TL["scenes"]:
        if t >= s["start"] - 0.05: cur = s
    return cur

def chyron(d, t, s):
    items = [(k, h, a if a is not None else s["start"] + 0.4) for k, h, a in CHY.get(s["name"], [])]
    items = [i for i in items if t >= i[2]]
    if not items: return
    k, h, a = items[-1]; lt = t - a; out = s["end"] + 0.3 - t
    p = ease(lt / 0.45) * (ease(out / 0.35) if out < 0.35 else 1)
    if p <= 0: return
    y = 1340; x0 = 40
    fk, fh = font(30), font(46)
    hw = d.textlength(h, font=fh)
    if hw > W - 120: fh = font(int(46 * (W - 120) / hw)); hw = d.textlength(h, font=fh)
    kw = d.textlength(k, font=fk)
    wbar = int((hw + 60) * p)
    d.rectangle([x0, y + 50, x0 + wbar, y + 128], fill=(12, 14, 22, 225))
    d.rectangle([x0, y + 50, x0 + 8, y + 128], fill=RED)
    kc = YEL if "UNBEST" in k else RED
    d.rectangle([x0, y, x0 + int((kw + 36) * p), y + 50], fill=kc + (255,))
    if p > 0.6:
        a_ = int(255 * clamp((p - 0.6) / 0.4))
        d.text((x0 + 18, y + 8), k, font=fk, fill=(0, 0, 0, a_) if kc == YEL else (255, 255, 255, a_))
        d.text((x0 + 30, y + 64), h, font=fh, fill=(255, 255, 255, a_))

# caption groups: max 4 words or sentence end
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
                d.text((x, y), w["w"], font=f, fill=col, stroke_width=5, stroke_fill=(0, 0, 0))
                x += d.textlength(w["w"], font=f) + sp
            return

TOPBAR = Image.new("RGBA", (W, 96), (0, 0, 0, 0)); td = ImageDraw.Draw(TOPBAR)
td.rectangle([0, 0, W, 96], fill=(0, 0, 0, 150))
td.text((80, 24), "DER DECODER", font=font(40), fill=WHITE)
lab = "KI-GENERIERT"; td.text((W - 40 - td.textlength(lab, font=font(28, False)), 32), lab, font=font(28, False), fill=GREY)

STILL = int(sys.argv[4]) if len(sys.argv) > 4 else None
ff = None if STILL is not None else subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-i", f"{WORK}/mix.wav", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                       "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", OUT], stdin=subprocess.PIPE)
last = None
for fi in ([STILL] if STILL is not None else range(NF)):
    t = fi / FPS
    try: img = Image.open(f"{FR}/f{fi:05d}.jpg").convert("RGB"); last = img
    except FileNotFoundError: img = last
    img = img.resize((W, H), Image.LANCZOS)
    # soft vignette-ish bottom gradient for legibility
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for i in range(0, 520, 8): d.rectangle([0, H - 520 + i, W, H - 512 + i], fill=(0, 0, 0, int(150 * i / 520)))
    ov.alpha_composite(TOPBAR)
    if int(t * 1.6) % 2 == 0: d.ellipse([36, 36, 60, 60], fill=RED)
    s = scene_at(t)
    chyron(d, t, s)
    captions(d, t)
    d.rectangle([0, H - 8, int(W * t / TL["total"]), H], fill=RED)
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    if STILL is not None: img.save(OUT); break
    ff.stdin.write(img.tobytes())
if ff: ff.stdin.close(); ff.wait()
print("done", OUT)
