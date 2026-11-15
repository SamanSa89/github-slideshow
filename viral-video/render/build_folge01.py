"""Renders Decoder episode 01 as a 1080x1920 MP4 (offline TTS via espeak-ng/MBROLA)."""
import math, os, re, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else "folge-01.mp4"
WORK = sys.argv[2] if len(sys.argv) > 2 else "work"
os.makedirs(WORK, exist_ok=True)
W, H, FPS, SR = 1080, 1920, 30, 22050
F = "/usr/share/fonts/truetype/dejavu/"
font = lambda s, b=True: ImageFont.truetype(F + ("DejaVuSans-Bold.ttf" if b else "DejaVuSans.ttf"), s)
RED, WHITE, GREY, BG, CYAN = (230, 40, 50), (245, 245, 245), (150, 150, 160), (12, 12, 18), (80, 220, 255)

# (scene, caption text, spoken text or None=same). *word* = red highlight in caption
SEG = [
 ("hook", "Wer hat den *Schalter*?", None),
 ("hook", "Drei Nachrichten von dieser Woche.", None),
 ("hook", "Die Medien zeigen sie dir einzeln. Ich zeige sie dir *zusammen*.", None),
 ("shenzhen", "Trump. Xi. Putin. Drei Männer, ein Raum. *Shenzhen*, nächste Woche.", "Trump. Schi. Putin. Drei Männer, ein Raum. Schenschen, nächste Woche."),
 ("shenzhen", "Thema: Kriege beenden, Atomwaffen.", None),
 ("shenzhen", "Weißt du, wer nicht eingeladen ist? *Du.* Und Europa auch nicht.", None),
 ("shenzhen", "Peking sagt offiziell nur: Wir reden darüber. Merk dir das.", None),
 ("starlink", "Ukraine. Abfangdrohnen jagen Kampfdrohnen.", None),
 ("starlink", "Bei *161 km/h*: Klick. Starlink aus. Drohne weg.", "Bei hunderteinundsechzig Kilometern pro Stunde: Klick. Starlink aus. Drohne weg."),
 ("starlink", "Selenskyj sagt: Das passiert nur in der Ukraine. In der EU nicht.", "Selenski sagt: Das passiert nur in der Ukraine. In der E U nicht."),
 ("starlink", "Washington sagt: technische Probleme.", "Woschington sagt: technische Probleme."),
 ("starlink", "Seit wann fragen technische Probleme nach deinem *Reisepass*?", None),
 ("faa", "USA. Freitag, der 13. Landesweiter Flugstopp.", "U S A. Freitag, der dreizehnte. Landesweiter Flugstopp."),
 ("faa", "Fast *8.000* gestrichene Flüge.", "Fast achttausend gestrichene Flüge."),
 ("faa", "Erst ein Router. Dann ein Update. Dann alte Geräte. *Drei Erklärungen* in 24 Stunden.", "Erst ein Ruuter. Dann ein Apdeit. Dann alte Geräte. Drei Erklärungen in vierundzwanzig Stunden."),
 ("faa", "Cyberangriff? Die Regierung sagt nein. Beweise fürs Gegenteil? Habe ich *keine*.", "Seiberangriff? Die Regierung sagt nein. Beweise fürs Gegenteil? Habe ich keine."),
 ("faa", "Darum behaupte ich es nicht. Merk dir den Unterschied.", None),
 ("gem", "Jetzt Gematria. Shenzhen: *99*. Rückwärts: *117*.", "Jetzt Gematria. Schenschen: neunundneunzig. Rückwärts: hundertsiebzehn."),
 ("gem", "Trump Xi Putin: *201*. Decode: *36*. Sechs mal sechs.", "Trump Schi Putin: zweihunderteins. Dikoud: sechsunddreißig. Sechs mal sechs."),
 ("gem", "Gänsehaut? Ich habe mir die gruselige Zahl vorher *ausgesucht*.", None),
 ("gem", "Genau so funktioniert das. Die echten Zahlen: *161 km/h* und *8.000 Flüge*.", "Genau so funktioniert das. Die echten Zahlen: hunderteinundsechzig Kilometer pro Stunde, und achttausend Flüge."),
 ("end", "Es braucht keinen geheimen Club. Alles passiert *öffentlich*.", None),
 ("end", "Ein Gipfel ohne dich. Ein Satellitennetz, das über eine Front entscheidet. Ein Router, an dem ein Land hängt.", "Ein Gipfel ohne dich. Ein Satellitennetz, das über eine Front entscheidet. Ein Ruuter, an dem ein Land hängt."),
 ("end", "Die Frage ist nicht: Wer steckt dahinter?", None),
 ("end", "Sondern: Warum gibt es so *wenige Schalter*?", None),
 ("cta", "Glaub mir nicht. *Prüf mich.* Quellen in der Beschreibung.", None),
 ("cta", "Ich bin der Decoder. Wir sehen uns nach Shenzhen.", "Ich bin der Dikouder. Wir sehen uns nach Schenschen."),
]

# ---------- audio ----------
GAP = 0.12
pcm, timeline, t = [], [], 0.6
pcm.append(np.zeros(int(SR * 0.6), np.int16))
for i, (scene, cap, spk) in enumerate(SEG):
    txt = spk or re.sub(r"\*", "", cap)
    wav = f"{WORK}/s{i:02d}.wav"
    subprocess.run(["espeak-ng", "-v", "mb-de6", "-s", "200", "-p", "38", "-w", wav, txt], check=True, capture_output=True)
    with wave.open(wav) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16)
        sr = w.getframerate()
    if sr != SR:
        a = np.interp(np.linspace(0, len(a), int(len(a) * SR / sr), endpoint=False), np.arange(len(a)), a).astype(np.int16)
    d = len(a) / SR
    timeline.append((t, t + d, scene, cap))
    pcm += [a, np.zeros(int(SR * GAP), np.int16)]
    t += d + GAP
pcm.append(np.zeros(int(SR * 1.2), np.int16))
voice = np.concatenate(pcm)
TOTAL = len(voice) / SR
with wave.open(f"{WORK}/voice.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(voice.tobytes())
env = np.abs(voice.astype(np.float32)) / 32768
hop = SR // FPS
rms = np.array([env[i * hop:(i + 1) * hop].mean() if i * hop < len(env) else 0 for i in range(int(TOTAL * FPS) + 2)])
rms = np.clip(rms / (rms.max() + 1e-6) * 1.8, 0, 1)

# ---------- caption chunks ----------
chunks = []
for (a, b, scene, cap) in timeline:
    words = cap.split()
    groups, g = [], []
    for wd in words:
        g.append(wd)
        if len(g) >= 3 or wd[-1] in ".?!:":
            groups.append(g); g = []
    if g: groups.append(g)
    lens = [sum(len(x) for x in gg) + 2 for gg in groups]
    tt = a
    for gg, L in zip(groups, lens):
        d = (b - a) * L / sum(lens)
        chunks.append((tt, tt + d, gg)); tt += d

def scene_at(t):
    for a, b, s, _ in timeline:
        if t < b + GAP: return s, t - timeline[[x[2] for x in timeline].index(s)][0]
    return "cta", t

# ---------- drawing ----------
def ctext(d, y, s, f, fill):
    w = d.textlength(s, font=f); d.text(((W - w) / 2, y), s, font=f, fill=fill)

def avatar(d, cx, cy, r, level, t):
    for k in range(6, 0, -1):
        d.ellipse([cx - r - k * 6, cy - r - k * 6, cx + r + k * 6, cy + r + k * 6], outline=(20, 60 + k * 10, 90 + k * 12), width=2)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(18, 22, 32), outline=CYAN, width=5)
    for yy in range(cy - r + 10, cy + r, 14):  # scanlines
        half = math.sqrt(max(r * r - (yy - cy) ** 2, 0)) - 8
        d.line([cx - half, yy, cx + half, yy], fill=(25, 35, 50), width=2)
    blink = (t % 4.2) < 0.12
    for ex in (-r * 0.36, r * 0.36):
        eh = 4 if blink else 22
        d.rounded_rectangle([cx + ex - 34, cy - r * 0.2 - eh, cx + ex + 34, cy - r * 0.2 + eh], 10, fill=CYAN)
    mh = 6 + level * 60; mw = 90 + level * 30
    d.rounded_rectangle([cx - mw, cy + r * 0.35 - mh / 2, cx + mw, cy + r * 0.35 + mh / 2], 14, fill=RED if level > 0.05 else (90, 30, 35))

def ease(x): return 1 - (1 - min(max(x, 0), 1)) ** 3

def graphic(d, scene, lt, t):
    y0 = 760
    if scene == "hook":
        on = int(t * 2) % 2 == 0
        d.rounded_rectangle([390, y0, 690, y0 + 360], 40, fill=(40, 40, 50), outline=GREY, width=4)
        d.rounded_rectangle([450, y0 + 40 + (0 if on else 150), 630, y0 + 170 + (0 if on else 150)], 24, fill=RED)
        ctext(d, y0 + 390, "WER HAT DEN SCHALTER?", font(70), WHITE)
    elif scene == "shenzhen":
        d.rounded_rectangle([90, y0, 990, y0 + 420], 30, outline=(60, 60, 75), width=3)
        for i, n in enumerate(["TRUMP", "XI", "PUTIN"]):
            x = 240 + i * 300; p = ease(lt * 1.5 - i * 0.3)
            if p <= 0: continue
            d.ellipse([x - 80, y0 + 60, x + 80, y0 + 220], fill=(50, 50, 62)); d.rounded_rectangle([x - 110, y0 + 220, x + 110, y0 + 330], 50, fill=(50, 50, 62))
            ctext_x = x - d.textlength(n, font=font(44)) / 2; d.text((ctext_x, y0 + 345), n, font=font(44), fill=WHITE)
        ctext(d, y0 + 450, "SHENZHEN · 19.11. · APEC", font(54), RED)
        if lt > 4: ctext(d, y0 + 525, "EUROPA: NICHT EINGELADEN", font(46), GREY)
    elif scene == "starlink":
        cx, cy, r = 540, y0 + 300, 270
        d.arc([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=(60, 60, 75), width=30)
        v = min(lt / 4, 1) * 161; ang = math.radians(180 + v / 200 * 180)
        d.arc([cx - r, cy - r, cx + r, cy + r], 180 + 161 / 200 * 180, 360, fill=RED, width=30)
        d.line([cx, cy, cx + (r - 40) * math.cos(ang), cy + (r - 40) * math.sin(ang)], fill=WHITE, width=12)
        ctext(d, cy + 30, f"{int(v)} km/h", font(80), RED if v >= 161 else WHITE)
        if v >= 161: ctext(d, cy + 130, "STARLINK: OFFLINE", font(56), RED)
    elif scene == "faa":
        rows = [("JFK", "ATL"), ("ORD", "LAX"), ("DFW", "SEA"), ("BOS", "MIA"), ("DEN", "SFO")]
        for i, (a, b) in enumerate(rows):
            y = y0 + i * 80
            d.rectangle([110, y, 970, y + 68], fill=(25, 25, 30))
            d.text((130, y + 10), f"{a} → {b}", font=font(44), fill=(255, 200, 60))
            if lt * 2.5 > i: d.text((640, y + 10), "CANCELLED", font=font(44), fill=RED)
        n = int(min(lt / 4, 1) * 8000)
        ctext(d, y0 + 420, f"{n:,}".replace(",", ".") + " FLÜGE GESTRICHEN", font(56), WHITE)
        ctext(d, y0 + 495, "FREITAG, 13.11.2026", font(40), GREY)
    elif scene == "gem":
        items = [("SHENZHEN", "99 / 117"), ("TRUMP XI PUTIN", "201"), ("DECODE", "36 = 6×6")]
        for i, (k, v) in enumerate(items):
            if lt > i * 2.5:
                d.text((140, y0 + 8 + i * 115), k, font=font(52), fill=GREY); tw = d.textlength(v, font=font(60)); d.text((940 - tw, y0 + i * 115), v, font=font(60), fill=CYAN)
        if lt > 9:
            d.line([120, y0 + 30, 960, y0 + 330], fill=RED, width=10); d.line([120, y0 + 330, 960, y0 + 30], fill=RED, width=10)
            ctext(d, y0 + 400, "AUSWAHL ≠ ENTSCHLÜSSELUNG", font(56), RED)
            ctext(d, y0 + 480, "ECHT: 161 km/h · 8.000 FLÜGE", font(50), WHITE)
    elif scene == "end":
        for i, s in enumerate(["GIPFEL OHNE DICH", "SATELLIT ENTSCHEIDET FRONT", "EIN ROUTER, EIN LAND"]):
            if lt > i * 2.2: ctext(d, y0 + 40 + i * 110, s, font(56), WHITE)
        if lt > 9: ctext(d, y0 + 420, "WARUM SO WENIGE SCHALTER?", font(54), RED)
    elif scene == "cta":
        ctext(d, y0 + 60, "PRÜF MICH.", font(130), RED)
        ctext(d, y0 + 240, "QUELLEN IN DER BESCHREIBUNG", font(52), WHITE)
        ctext(d, y0 + 330, "DER DECODER", font(70), CYAN)

scene_start = {}
for a, b, s, _ in timeline: scene_start.setdefault(s, a)

def caption(d, t):
    for a, b, g in chunks:
        if a <= t < b:
            parts = [(re.sub(r"[*]", "", w), w.startswith("*") or w.endswith("*") or "*" in w) for w in g]
            f = font(78); sp = d.textlength(" ", font=f)
            tot = sum(d.textlength(p, font=f) for p, _ in parts) + sp * (len(parts) - 1)
            if tot > W - 80: f = font(int(78 * (W - 80) / tot)); sp = d.textlength(" ", font=f); tot = W - 80
            x = (W - tot) / 2; y = 1450
            d.rounded_rectangle([x - 30, y - 20, x + tot + 30, y + f.size + 30], 20, fill=(0, 0, 0))
            for p, hl in parts:
                d.text((x, y), p, font=f, fill=RED if hl else WHITE, stroke_width=3, stroke_fill=(0, 0, 0)); x += d.textlength(p, font=f) + sp
            return

NF = int(TOTAL * FPS)
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-i", f"{WORK}/voice.wav", "-f", "lavfi", "-t", str(TOTAL), "-i", "sine=f=55:sample_rate=22050",
                       "-f", "lavfi", "-t", str(TOTAL), "-i", "sine=f=82.5:sample_rate=22050",
                       "-filter_complex", "[1:a]highpass=f=90,acompressor=threshold=-18dB:ratio=3,volume=1.6[v];[2:a][3:a]amix=inputs=2,volume=0.05,tremolo=f=0.5:d=0.6[m];[v][m]amix=inputs=2:duration=first:normalize=0[a]",
                       "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", OUT], stdin=subprocess.PIPE)
prev = None
for fi in range(NF):
    t = fi / FPS
    scene = "hook"
    for a, b, s, _ in timeline:
        if t >= a - 0.01: scene = s
    lt = t - scene_start[scene]
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    for gy in range(0, H, 60): d.line([0, gy, W, gy], fill=(18, 18, 26))
    d.rectangle([0, 0, W, 110], fill=(0, 0, 0)); d.text((40, 30), "● DER DECODER", font=font(46), fill=RED)
    lab = "KI-GENERIERT"; d.text((W - 40 - d.textlength(lab, font=font(34, False)), 40), lab, font=font(34, False), fill=GREY)
    lvl = float(rms[min(fi, len(rms) - 1)])
    punch = 1.0
    if scene != prev and fi: punch = 1.0
    avatar(d, 540, 420, 220, lvl, t)
    graphic(d, scene, lt, t)
    caption(d, t)
    pr = t / TOTAL; d.rectangle([0, H - 14, int(W * pr), H], fill=RED)
    d.text((40, H - 90), "Quellen: CNN · CBS · Al Jazeera · Ukrainska Pravda · SCMP", font=font(30, False), fill=GREY)
    if fi - int(scene_start[scene] * FPS) < 4 and scene != "hook":
        img = img.resize((int(W * 1.04), int(H * 1.04))).crop((int(W * .02), int(H * .02), int(W * .02) + W, int(H * .02) + H))
    ff.stdin.write(img.tobytes()); prev = scene
ff.stdin.close(); ff.wait()
print(f"done {OUT} {TOTAL:.1f}s")
