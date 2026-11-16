"""Decoder episode 01 – v3: flowing neural voice, procedural beat + SFX, kinetic animations.

usage: PIPER_MODEL=path/de-thorsten-low.onnx python3 build_folge01_v3.py out.mp4 workdir
"""
import math, os, random, re, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from piper import PiperVoice, SynthesisConfig
from host import body, sprites

OUT = sys.argv[1] if len(sys.argv) > 1 else "folge-01.mp4"
WORK = sys.argv[2] if len(sys.argv) > 2 else "work"
os.makedirs(WORK, exist_ok=True)
W, H, FPS, SR = 1080, 1920, 30, 44100
TOP = 975  # host area height
random.seed(7); rng = np.random.default_rng(7)
FD = "/usr/share/fonts/truetype/dejavu/"
_fc = {}
def font(s, b=True):
    k = (s, b)
    if k not in _fc: _fc[k] = ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if b else "DejaVuSans.ttf"), s)
    return _fc[k]
RED, WHITE, GREY, BG, CYAN, YEL = (232, 38, 52), (246, 246, 246), (150, 150, 165), (11, 11, 17), (80, 220, 255), (255, 214, 60)

# --------------------------------------------------------------------------- script
# caption (with *highlight*), spoken text (None = caption without *)
SCRIPT = [
 ("hook", [
   ("Wer hat eigentlich den *Schalter*?", None),
   ("Drei Nachrichten aus dieser Woche. Die Medien zeigen sie dir einzeln, ich zeige sie dir *zusammen*.", None)]),
 ("shenzhen", [
   ("Trump, Xi und Putin treffen sich nächste Woche in *Shenzhen*, um über Krieg und Atomwaffen zu reden.",
    "Trump, Schi und Putin treffen sich nächste Woche in Schenschen, um über Krieg und Atomwaffen zu reden."),
   ("Und weißt du, wer nicht eingeladen ist? *Du.* Und Europa übrigens auch nicht.", None),
   ("Peking sagt offiziell nur: Wir reden darüber. Merk dir das.", None)]),
 ("starlink", [
   ("In der Ukraine jagen Abfangdrohnen russische Kampfdrohnen.", None),
   ("Doch ab *161 km/h* macht es *Klick*, Starlink schaltet ab, und die Drohne ist weg.",
    "Doch ab hunderteinundsechzig Kilometern pro Stunde macht es Klick, Starlink schaltet ab, und die Drohne ist weg."),
   ("Selenskyj sagt, das passiert nur in der Ukraine, in der EU nicht.", "Selenski sagt, das passiert nur in der Ukraine, in der E U nicht."),
   ("Washington nennt es technische Probleme. Seit wann fragen technische Probleme nach deinem *Reisepass*?", None)]),
 ("faa", [
   ("Und dann, Freitag, der Dreizehnte: In den USA steht plötzlich der komplette Luftraum still.",
    "Und dann, Freitag, der dreizehnte: In den U S A steht plötzlich der komplette Luftraum still."),
   ("Fast *8.000* Flüge gestrichen.", "Fast achttausend Flüge gestrichen."),
   ("Erst war es ein Router, dann ein Update, dann alte Geräte. *Drei Erklärungen* in 24 Stunden.",
    "Erst war es ein Ruuter, dann ein Apdeit, dann alte Geräte. Drei Erklärungen in vierundzwanzig Stunden."),
   ("Ein Cyberangriff? Die Regierung sagt nein, und ich habe *keine* Beweise fürs Gegenteil. Darum behaupte ich es auch nicht.",
    "Ein Saiberangriff? Die Regierung sagt nein, und ich habe keine Beweise fürs Gegenteil. Darum behaupte ich es auch nicht.")]),
 ("gem", [
   ("Jetzt der Teil, auf den alle warten: Gematria.", None),
   ("Shenzhen ergibt *99*, rückwärts *117*. Trump Xi Putin ergibt *201*, und Decode ergibt *36*, sechs mal sechs.",
    "Schenschen ergibt neunundneunzig, rückwärts hundertsiebzehn. Trump Schi Putin ergibt zweihunderteins, und Dikoud ergibt sechsunddreißig, sechs mal sechs."),
   ("Gänsehaut? Ich habe mir die gruselige Zahl vorher *ausgesucht*. Genau so funktioniert dieser Trick.", None),
   ("Die echten Zahlen sind *161 km/h* und *8.000 Flüge*.",
    "Die echten Zahlen sind hunderteinundsechzig Kilometer pro Stunde, und achttausend Flüge.")]),
 ("end", [
   ("Und hier ist die Wahrheit, die unbequemer ist als jede Verschwörung: Es braucht keinen geheimen Club. Alles passiert *öffentlich*.", None),
   ("Ein Gipfel ohne dich, ein Satellitennetz, das über eine Front entscheidet, und ein Router, an dem ein ganzes Land hängt.",
    "Ein Gipfel ohne dich, ein Satellitennetz, das über eine Front entscheidet, und ein Ruuter, an dem ein ganzes Land hängt."),
   ("Die Frage ist nicht, wer dahintersteckt. Die Frage ist: Warum gibt es so *wenige Schalter*?", None)]),
 ("cta", [
   ("Also glaub mir nicht. *Prüf mich.* Die Quellen stehen in der Beschreibung.", None),
   ("Ich bin der Decoder. Wir sehen uns nach Shenzhen.", "Ich bin der Dikouder. Wir sehen uns nach Schenschen.")]),
]

# --------------------------------------------------------------------------- voice
voice = PiperVoice.load(os.environ.get("PIPER_MODEL", "de-thorsten-low.onnx"))
cfg = SynthesisConfig(length_scale=0.97, noise_scale=0.72, noise_w_scale=0.9)
VSR = 16000
def sil(s): return np.zeros(int(VSR * s), np.float32)
parts, words, scenes = [sil(0.5)], [], []   # words: (t0, t1, text, hl, scene)
t = 0.5
for si, (scene, sents) in enumerate(SCRIPT):
    if si: parts.append(sil(0.35)); t += 0.35
    scenes.append([scene, t, None])
    for cap, spk in sents:
        txt = spk or cap.replace("*", "")
        chunks = list(voice.synthesize(txt, cfg))
        seg = []
        for ci, c in enumerate(chunks):
            a = c.audio_float_array.astype(np.float32)
            seg.append(a)
            if ci < len(chunks) - 1: seg.append(sil(0.22))
        a = np.concatenate(seg); d = len(a) / VSR
        # distribute caption words over sentence duration (weight: chars + pause after punctuation)
        ws = cap.split()
        wt = [len(w.replace("*", "")) + 2 + (5 if w[-1] in ",:" else 0) + (8 if w.rstrip("*")[-1] in ".?!" else 0) for w in ws]
        tt = t
        for w, k in zip(ws, wt):
            dd = d * k / sum(wt)
            words.append((tt, tt + dd, w.replace("*", ""), "*" in w, scene)); tt += dd
        parts += [a, sil(0.3)]; t += d + 0.3
    scenes[-1][2] = t
parts.append(sil(1.6)); t += 1.6
TOTAL = t
v16 = np.concatenate(parts)
def wav_write(path, a, sr):
    a = np.clip(a, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((a * 32767).astype(np.int16).tobytes())
def wav_read(path):
    with wave.open(path) as w: return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
wav_write(f"{WORK}/v16.wav", v16 / (np.abs(v16).max() + 1e-6) * 0.9, VSR)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{WORK}/v16.wav", "-af",
                "aresample=44100:resampler=soxr,highpass=f=75,equalizer=f=160:t=q:w=1:g=3,equalizer=f=3200:t=q:w=1.4:g=3,"
                "deesser=i=0.4,acompressor=threshold=-22dB:ratio=3.5:attack=4:release=90:makeup=4,aecho=0.8:0.45:25|48:0.07|0.04",
                "-ac", "1", f"{WORK}/v44.wav"], check=True)
V = wav_read(f"{WORK}/v44.wav")
N = int(TOTAL * SR); V = np.pad(V, (0, max(0, N - len(V))))[:N]

def scene_t(name): return next(s for s in scenes if s[0] == name)
def word_t(scene, token, nth=0):
    hits = [w for w in words if w[4] == scene and token.lower() in w[2].lower()]
    return hits[min(nth, len(hits) - 1)][0] if hits else scene_t(scene)[1]

# --------------------------------------------------------------------------- music + sfx
tt_ = lambda d: np.arange(int(d * SR)) / SR
def env(d, a=0.005, r=None):
    n = int(d * SR); e = np.ones(n); na = max(1, int(a * SR)); e[:na] = np.linspace(0, 1, na)
    if r: e *= np.exp(-np.arange(n) / (r * SR))
    return e
def onepole_lp(x, fc):  # vectorised-ish one-pole lowpass with per-sample cutoff
    fc = np.broadcast_to(fc, x.shape); a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); z = 0.0
    for i in range(len(x)): z = (1 - a[i]) * x[i] + a[i] * z; y[i] = z
    return y
def noise(d): return rng.uniform(-1, 1, int(d * SR))
def sfx_kick():
    t = tt_(0.5); f = 45 + 110 * np.exp(-t * 28); return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
def sfx_clap():
    n = noise(0.25); n = n - onepole_lp(n, 900); e = np.exp(-tt_(0.25) * 22)
    for o in (0.0, 0.012, 0.024): e[int(o * SR):int(o * SR) + 200] += 0.6
    return n * e * 0.8
def sfx_hat(open_=False):
    d = 0.18 if open_ else 0.05; n = noise(d); n = n - onepole_lp(n, 6000); return n * np.exp(-tt_(d) * (15 if open_ else 70)) * 0.35
def sfx_808(f, d):
    t = tt_(d); x = np.sin(2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * f * t)); return np.tanh(1.6 * x) * np.minimum(1, t * 80) * np.exp(-t * 1.4)
def sfx_whoosh(d=0.55, up=True):
    t = tt_(d); n = noise(d); fc = (300 + 5000 * (t / d if up else 1 - t / d)); e = np.sin(np.pi * t / d) ** 2
    return onepole_lp(n, fc) * e * 1.4
def sfx_impact():
    t = tt_(1.6); f = 32 + 70 * np.exp(-t * 9); b = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    n = onepole_lp(noise(1.6), 1800) * np.exp(-t * 9) * 0.8; return np.tanh(1.8 * (b + n))
def sfx_click():
    t = tt_(0.04); return (np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 300) + noise(0.04) * np.exp(-t * 500)) * 0.7
def sfx_powerdown():
    t = tt_(0.9); f = 900 * np.exp(-t * 4) + 40; return np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t * 3) * 0.25
def sfx_flap():
    out = np.zeros(int(0.25 * SR))
    for k in range(6):
        c = sfx_click() * 0.5; o = int(k * 0.035 * SR); out[o:o + len(c)] += c[:len(out) - o]
    return out
def sfx_tick(): t = tt_(0.02); return np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 400) * 0.35
def sfx_ding():
    t = tt_(1.2); return (np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 1976 * t)) * np.exp(-t * 4) * 0.4
def sfx_blip(f=1046):
    t = tt_(0.12); return np.sign(np.sin(2 * np.pi * f * t)) * np.exp(-t * 30) * 0.18
def sfx_buzzer():
    t = tt_(0.45); return np.tanh(3 * np.sin(2 * np.pi * 110 * t) + np.sin(2 * np.pi * 116 * t)) * env(0.45, 0.005, 0.25) * 0.4
def sfx_riser(d=1.4):
    t = tt_(d); f = 200 + 1800 * (t / d) ** 2; return (np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3 + onepole_lp(noise(d), 300 + 6000 * t / d) * 0.8) * (t / d) ** 2
def sfx_glitch(d=0.28):
    x = noise(d); step = rng.integers(20, 200)
    x = np.repeat(x[::step], step)[:int(d * SR)]; x = np.round(x * 4) / 4
    return x * 0.3 * (rng.uniform(size=len(x)) > 0.3)
def sfx_pop():
    t = tt_(0.1); f = 900 * np.exp(-t * 30) + 200; return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 35) * 0.5
def sfx_stamp(): return sfx_impact()[:int(0.5 * SR)] * np.exp(-tt_(0.5) * 6) * 0.9 + np.pad(sfx_click(), (0, int(0.46 * SR)))[:int(0.5 * SR)]

MUS = np.zeros(N); FX = np.zeros(N)
def add(buf, x, at, g=1.0):
    i = int(at * SR)
    if i >= N or i + len(x) <= 0: return
    if i < 0: x = x[-i:]; i = 0
    x = x[:N - i]; buf[i:i + len(x)] += x * g

BPM = 92; beat = 60 / BPM; step = beat / 4
K, C, HC, HO = sfx_kick(), sfx_clap(), sfx_hat(), sfx_hat(True)
prog = [55.0, 43.65, 65.41, 49.0]
beat_start = scene_t("hook")[1] + 0.2
kick_times = []
drop = (scene_t("end")[1], scene_t("end")[1] + 3.2)   # breakdown for drama
bar = 0; tb = beat_start
while tb < TOTAL - 1.2:
    full = tb >= scene_t("shenzhen")[1] - 0.05
    in_drop = drop[0] <= tb < drop[1]
    add(MUS, sfx_808(prog[bar % 4], beat * 4), tb, 0.5 if not in_drop else 0.0)
    for s in range(16):
        ts = tb + s * step
        if in_drop: continue
        if full and s in (0, 7, 10): add(MUS, K, ts, 0.9); kick_times.append(ts)
        if not full and s in (0, 8): add(MUS, K, ts, 0.6); kick_times.append(ts)
        if full and s in (4, 12): add(MUS, C, ts, 0.55)
        if s % 2 == 0: add(MUS, HC, ts, 0.5 if full else 0.3)
        if full and bar % 2 == 1 and s in (13, 14, 15): add(MUS, HC, ts + step / 2, 0.35)
        if full and s == 14 and bar % 4 == 3: add(MUS, HO, ts, 0.5)
    # pad: minor chord drone
    tpad = tt_(beat * 4)
    pad = sum(np.sin(2 * np.pi * f * tpad + np.sin(2 * np.pi * 0.3 * tpad)) for f in (prog[bar % 4] * 4, prog[bar % 4] * 4 * 1.189, prog[bar % 4] * 6))
    add(MUS, pad * np.sin(np.pi * tpad / (beat * 4)) ** 0.5 * 0.05, tb)
    tb += beat * 4; bar += 1
kick_times = np.array(kick_times)

# sidechain duck under voice
venv = np.abs(V); k = int(0.08 * SR)
venv = np.convolve(venv, np.ones(k) / k, mode="same")
duck = 1 - 0.65 * np.clip(venv / (venv.max() * 0.25 + 1e-6), 0, 1)
MUS *= duck

# --------------------------------------------------------------------------- events (visual + sound)
EV = []   # (time, kind, payload)
def ev(t, kind, payload=None): EV.append((t, kind, payload))
for name, t0, t1 in scenes:
    if name != "hook":
        add(FX, sfx_whoosh(0.5), t0 - 0.35, 0.8); ev(t0, "flash"); ev(t0, "glitch", 0.18)
# highlights -> kinetic popup + pop/hit
for (a, b, w, hl, sc) in words:
    if hl:
        txt = re.sub(r"[,.?!]$", "", w).upper()
        ev(a, "pop", txt); add(FX, sfx_pop(), a, 0.6); ev(a, "punch")
# merge consecutive highlighted words into one popup (e.g. "161 km/h", "Drei Erklärungen")
merged, i = [], 0
pops = [e for e in EV if e[1] == "pop"]; EV = [e for e in EV if e[1] != "pop"]
while i < len(pops):
    t0, _, txt = pops[i]; j = i + 1
    while j < len(pops) and pops[j][0] - pops[j - 1][0] < 0.6: txt += " " + pops[j][2]; j += 1
    merged.append((t0, "pop", txt)); i = j
EV += merged
# hook
h0 = scene_t("hook")[1]
add(FX, sfx_glitch(0.35), h0 - 0.2, 1.0); add(FX, sfx_impact(), h0, 0.9); ev(h0, "shake", 1.0); ev(h0, "glitch", 0.35)
for k_ in range(4): add(FX, sfx_click(), h0 + 0.6 + k_ * 0.5, 0.7)
add(FX, sfx_impact(), word_t("hook", "zusammen"), 0.6); ev(word_t("hook", "zusammen"), "shake", 0.6)
# shenzhen
s0 = scene_t("shenzhen")[1]
for k_, nm in enumerate(["Trump", "Xi", "Putin"]): add(FX, sfx_pop(), word_t("shenzhen", nm), 0.7)
T_STAMP_EU = word_t("shenzhen", "Europa"); add(FX, sfx_stamp(), T_STAMP_EU, 0.9); ev(T_STAMP_EU, "shake", 0.5)
# starlink
T_KLICK = word_t("starlink", "Klick")
add(FX, sfx_click(), T_KLICK, 1.2); add(FX, sfx_powerdown(), T_KLICK + 0.05, 0.9); ev(T_KLICK, "glitch", 0.4); ev(T_KLICK, "shake", 0.7)
T_PASS = word_t("starlink", "Reisepass"); add(FX, sfx_impact(), T_PASS, 0.5)
# faa
f0 = scene_t("faa")[1]; T_FAA_STOP = word_t("faa", "Luftraum")
for k_ in range(5): add(FX, sfx_flap(), T_FAA_STOP + 0.35 * k_, 0.7)
T_COUNT = word_t("faa", "8.000")
for k_ in range(18): add(FX, sfx_tick(), T_COUNT + k_ * 0.06, 0.8)
add(FX, sfx_ding(), T_COUNT + 1.1, 0.8)
for nm in ("Router", "Update", "Geräte"): add(FX, sfx_blip(784), word_t("faa", nm), 1.0)
add(FX, sfx_buzzer(), word_t("faa", "Cyberangriff"), 0.6)
# gematria
g0 = scene_t("gem")[1]
add(FX, sfx_glitch(0.4), g0, 0.9)
T_GEM = [word_t("gem", "99"), word_t("gem", "201"), word_t("gem", "36")]
for tg in T_GEM:
    for k_ in range(8): add(FX, sfx_blip(600 + 120 * k_), tg - 0.5 + k_ * 0.06, 0.8)
T_X = word_t("gem", "ausgesucht"); add(FX, sfx_buzzer(), T_X, 0.9); ev(T_X, "shake", 0.6)
T_REAL = word_t("gem", "echten"); add(FX, sfx_ding(), T_REAL + 0.6, 0.6)
# end
e0 = scene_t("end")[1]
T_LINES = [word_t("end", "Gipfel"), word_t("end", "Satellitennetz"), word_t("end", "Router")]
for tl in T_LINES:
    for k_ in range(14): add(FX, sfx_tick(), tl + k_ * 0.045, 0.9)
T_Q = word_t("end", "Warum"); add(FX, sfx_riser(1.2), T_Q - 1.2, 0.6); add(FX, sfx_impact(), T_Q, 0.9); ev(T_Q, "shake", 0.8); ev(T_Q, "flash")
# cta
c0 = scene_t("cta")[1]; T_PRUEF = word_t("cta", "Prüf")
add(FX, sfx_riser(1.3), T_PRUEF - 1.3, 0.7); add(FX, sfx_stamp(), T_PRUEF, 1.0); ev(T_PRUEF, "shake", 1.0); ev(T_PRUEF, "glitch", 0.25)
T_FOLLOW = word_t("cta", "Decoder"); add(FX, sfx_click(), T_FOLLOW + 0.6, 1.0); add(FX, sfx_ding(), T_FOLLOW + 0.65, 0.5)
add(FX, sfx_impact(), TOTAL - 1.4, 0.7)

MUS *= 0.18 / 0.32
MIX = V * 1.0 + MUS * 0.32 + FX * 0.42
rms = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
print(f"levels dB  voice {rms(V):.1f}  music {rms(MUS * 0.32):.1f}  fx {rms(FX * 0.42):.1f}", flush=True)
MIX = np.tanh(MIX * 1.1) * 0.9
wav_write(f"{WORK}/mix.wav", MIX, SR)

# mouth envelope per frame
NF = int(TOTAL * FPS); hop = SR // FPS
vlev = np.array([np.sqrt(np.mean(V[i * hop:(i + 1) * hop] ** 2)) if i * hop < N else 0 for i in range(NF + 2)])
vlev = np.clip(vlev / (np.percentile(vlev[vlev > 0.002], 95) + 1e-6), 0, 1)

# --------------------------------------------------------------------------- visual helpers
def ease(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def back(x):  # overshoot ease
    x = min(max(x, 0), 1); c = 1.9; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def ctext(d, y, s, f, fill, x=None, stroke=0):
    w = d.textlength(s, font=f); d.text(((W - w) / 2 if x is None else x, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
def since(t, t0): return t - t0
def recent(kind, t, win):
    return [e for e in EV if e[1] == kind and 0 <= t - e[0] < win]

BODY = body(); HEADS = sprites()
hl_spans = [(a, b + 0.4) for a, b, w, hl, sc in words if hl]

def make_bg():
    im = Image.new("RGB", (W, TOP), BG); d = ImageDraw.Draw(im)
    for y in range(0, TOP, 3):
        k = y / TOP; d.rectangle([0, y, W, y + 3], fill=(int(12 + 14 * k), int(14 + 6 * k), int(36 - 18 * k)))
    for x in range(-200, W + 200, 90): d.line([x, TOP, x + 300, 0], fill=(22, 24, 44), width=2)
    d.text((50, 150), "DECODER", font=font(150), fill=(30, 28, 52))
    return im
BG_TOP = make_bg()
glow = Image.new("L", (W, TOP)); ImageDraw.Draw(glow).ellipse([160, 140, 920, 900], fill=255); glow = glow.filter(ImageFilter.GaussianBlur(130))
GLOW_RGB = Image.new("RGB", (W, TOP), (215, 30, 48))
PARTS = [(random.uniform(0, W), random.uniform(0, TOP), random.uniform(20, 60), random.uniform(2, 5)) for _ in range(40)]

def render_top(t, fi):
    kd = t - kick_times[kick_times <= t].max() if (kick_times <= t).any() else 9
    pulse = math.exp(-kd * 5)
    im = BG_TOP.copy()
    im.paste(GLOW_RGB, (0, 0), glow.point(lambda v: int(v * (0.45 + 0.4 * pulse))))
    d = ImageDraw.Draw(im, "RGBA")
    for (x, y, sp, r) in PARTS:
        yy = (y - t * sp) % TOP; d.ellipse([x - r, yy - r, x + r, yy + r], fill=(120, 200, 255, 60))
    sy = (t * 220) % (TOP + 200) - 100; d.rectangle([0, sy, W, sy + 3], fill=(120, 220, 255, 40))
    # host
    lvl = float(vlev[min(fi, len(vlev) - 1)])
    global mlev
    mlev = 0.5 * mlev + 0.5 * lvl
    m = 0 if mlev < 0.1 else 1 if mlev < 0.28 else 2 if mlev < 0.48 else 3 if mlev < 0.72 else 4
    blink = (t % 3.9) < 0.12 or (t % 8.3) < 0.1
    brow = 1 if any(a <= t < b for a, b in hl_spans) else 0
    q = any(a <= t < b and w.endswith("?") for a, b, w, hl, sc in words)
    bob = math.sin(t * 2.3) * 6 + mlev * 12
    tilt = math.sin(t * 0.8) * 2.5 + (4 if q else 0) + (2 if brow else 0)
    hd = HEADS[(m, blink, brow)].rotate(tilt, resample=Image.BICUBIC, center=(280, 560))
    im.paste(BODY, (130, 600 + int(bob * 0.4)), BODY); im.paste(hd, (260, 125 + int(bob)), hd)
    # camera: slow push per scene + punch on highlights + shake
    sc = current_scene(t); z = 1.0 + 0.05 * ease((t - sc[1]) / 8)
    for e in recent("punch", t, 0.35): z += 0.07 * (1 - (t - e[0]) / 0.35)
    if z > 1.001:
        nw, nh = int(W * z), int(TOP * z); im = im.resize((nw, nh), Image.BILINEAR)
        cx, cy = (nw - W) // 2, int((nh - TOP) * 0.35); im = im.crop((cx, cy, cx + W, cy + TOP))
    # kinetic popup text
    d = ImageDraw.Draw(im, "RGBA")
    for e in recent("pop", t, 1.1):
        k_ = (t - e[0]); s = back(k_ / 0.22); a = 255 if k_ < 0.8 else int(255 * (1 - (k_ - 0.8) / 0.3))
        f = font(max(10, int(118 * s))); txt = e[2]
        if d.textlength(txt, font=f) > W - 80: f = font(max(10, int(f.size * (W - 80) / d.textlength(txt, font=f))))
        tw = d.textlength(txt, font=f); x = (W - tw) / 2; y = 690
        d.rounded_rectangle([x - 26, y - 14, x + tw + 26, y + f.size + 24], 18, fill=(232, 38, 52, int(a * 0.92)))
        d.text((x, y), txt, font=f, fill=(255, 255, 255, a))
    return im

def current_scene(t):
    cur = scenes[0]
    for s in scenes:
        if t >= s[1] - 0.05: cur = s
    return cur

def panel(t, sc):
    name, t0, t1 = sc; lt = t - t0
    im = Image.new("RGBA", (W, 600), (0, 0, 0, 0)); d = ImageDraw.Draw(im, "RGBA"); y0 = 20
    if name == "hook":
        on = int((t - h0 - 0.6) / 0.5) % 2 == 0 if t > h0 + 0.6 else True
        d.rounded_rectangle([400, y0, 680, y0 + 330], 40, fill=(38, 38, 48), outline=GREY, width=4)
        d.rounded_rectangle([455, y0 + 35 + (0 if on else 140), 625, y0 + 155 + (0 if on else 140)], 24, fill=RED if on else (90, 30, 35))
        if on: d.rounded_rectangle([440, y0 + 20, 640, y0 + 170], 30, outline=(232, 38, 52, 90), width=8)
        ctext(d, y0 + 370, "WER HAT DEN SCHALTER?", font(70), WHITE, stroke=3)
    elif name == "shenzhen":
        # rotating globe + ping
        gx, gy, r = 230, y0 + 230, 190
        d.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(18, 30, 52), outline=CYAN, width=3)
        for k_ in range(6):
            ph = (lt * 0.6 + k_ / 6) % 1; ww = abs(math.cos(ph * math.pi)) * r
            d.ellipse([gx - ww, gy - r, gx + ww, gy + r], outline=(60, 140, 190, 120), width=2)
        for la in (-0.6, -0.3, 0, 0.3, 0.6):
            yy = gy + la * r; hw = math.sqrt(max(r * r - (la * r) ** 2, 0)); d.line([gx - hw, yy, gx + hw, yy], fill=(60, 140, 190, 120), width=2)
        px, py = gx + 70, gy + 40; pr = (lt * 60) % 80
        d.ellipse([px - pr, py - pr, px + pr, py + pr], outline=(232, 38, 52, int(255 * (1 - pr / 80))), width=5)
        d.ellipse([px - 12, py - 12, px + 12, py + 12], fill=RED)
        d.text((gx - 150, gy + r + 15), "SHENZHEN", font=font(34), fill=WHITE)
        for i, nm in enumerate(["TRUMP", "XI", "PUTIN"]):
            tp = word_t("shenzhen", nm.capitalize() if nm != "XI" else "Xi"); s = back((t - tp) / 0.25)
            if t < tp: continue
            x = 560 + i * 170; yy = y0 + 70
            rr = int(62 * s); d.ellipse([x - rr, yy, x + rr, yy + 2 * rr], fill=(52, 52, 66), outline=WHITE, width=3)
            fw = d.textlength(nm, font=font(34)); d.text((x - fw / 2, yy + 140), nm, font=font(34), fill=WHITE)
        ctext(d, y0 + 270, "19.11. · APEC-GIPFEL", font(46), RED, x=520)
        if t >= T_STAMP_EU:
            s = 1 + 1.2 * (1 - ease((t - T_STAMP_EU) / 0.2))
            f = font(52); sw = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength("EUROPA: NICHT EINGELADEN", font=f)) + 70
            st = Image.new("RGBA", (sw, 130)); sd = ImageDraw.Draw(st)
            sd.rounded_rectangle([5, 5, sw - 5, 125], 16, outline=RED, width=10)
            sd.text((35, 34), "EUROPA: NICHT EINGELADEN", font=f, fill=RED)
            st = st.rotate(-6, expand=True, resample=Image.BICUBIC); st = st.resize((int(st.width * s), int(st.height * s)))
            im.alpha_composite(st, (int(W / 2 - st.width / 2), int(y0 + 410 - st.height / 2)))
    elif name == "starlink":
        off = t >= T_KLICK; kt = t - T_KLICK
        sx = 120 + (lt * 60) % 840; sy = y0 + 40
        d.rectangle([sx - 18, sy - 12, sx + 18, sy + 12], fill=GREY); d.rectangle([sx - 60, sy - 8, sx - 22, sy + 8], fill=CYAN); d.rectangle([sx + 22, sy - 8, sx + 60, sy + 8], fill=CYAN)
        dx = 820; dy = y0 + 170 + (0 if not off else min(kt, 1.5) ** 2 * 260)
        if not off:
            for k_ in range(10):
                fx = sx + (dx - sx) * k_ / 10; fy = sy + (dy - sy) * k_ / 10
                if (k_ + int(t * 10)) % 2: d.line([fx, fy, fx + (dx - sx) / 20, fy + (dy - sy) / 20], fill=CYAN, width=4)
        rot = 0 if not off else kt * 400
        dr = Image.new("RGBA", (160, 80)); ddd = ImageDraw.Draw(dr)
        ddd.rectangle([50, 30, 110, 50], fill=WHITE); ddd.line([10, 20, 150, 20], fill=GREY, width=6); ddd.line([10, 60, 150, 60], fill=GREY, width=6)
        dr = dr.rotate(rot, expand=True)
        if dy < 600: im.alpha_composite(dr, (int(dx - dr.width / 2), int(dy - dr.height / 2)))
        cx, cy, r = 330, y0 + 420, 230
        d.arc([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=(60, 60, 75), width=28)
        d.arc([cx - r, cy - r, cx + r, cy + r], 180 + 161 / 200 * 180, 360, fill=RED, width=28)
        tsp = word_t("starlink", "161"); v = 161 * ease((t - (tsp - 1.5)) / 1.5) if t > tsp - 1.5 else 0
        jit = (random.uniform(-2, 2) if v > 150 and not off else 0)
        ang = math.radians(180 + (v + jit) / 200 * 180)
        d.line([cx, cy, cx + (r - 40) * math.cos(ang), cy + (r - 40) * math.sin(ang)], fill=WHITE, width=10)
        ctext(d, cy + 20, f"{int(v)} km/h", font(64), RED if v >= 160 else WHITE, x=cx - 120)
        if off and int(kt * 6) % 2 == 0: d.text((620, y0 + 400), "OFFLINE", font=font(76), fill=RED)
        if t >= T_PASS:
            s = back((t - T_PASS) / 0.25); f = font(int(46 * s)); d.text((610, y0 + 500), "NUR UKRAINE?", font=f, fill=YEL)
    elif name == "faa":
        px = -100 + min(lt / (T_FAA_STOP - f0 + 0.01), 1) * 640
        d.polygon([(px, y0 + 40), (px - 90, y0 + 20), (px - 90, y0 + 60)], fill=WHITE)
        d.polygon([(px - 40, y0 + 40), (px - 70, y0 - 5), (px - 55, y0 + 40), (px - 70, y0 + 85)], fill=GREY)
        if t > T_FAA_STOP: d.line([px - 110, y0, px + 20, y0 + 80], fill=RED, width=10); d.line([px - 110, y0 + 80, px + 20, y0], fill=RED, width=10)
        rows = [("JFK", "ATL"), ("ORD", "LAX"), ("DFW", "SEA"), ("BOS", "MIA"), ("DEN", "SFO")]
        for i, (a, b) in enumerate(rows):
            y = y0 + 120 + i * 66; d.rectangle([110, y, 970, y + 58], fill=(25, 25, 30))
            d.text((130, y + 8), f"{a} → {b}", font=font(40), fill=YEL)
            tf = T_FAA_STOP + 0.35 * i
            if t > tf: d.text((660, y + 8), "CANCELLED" if t > tf + 0.2 else random.choice(["ON TIME", "DELAYED", "#$%&@!"]), font=font(40), fill=RED)
            else: d.text((660, y + 8), "ON TIME", font=font(40), fill=(110, 200, 120))
        n = int(min(max(t - T_COUNT, 0) / 1.1, 1) * 8000)
        ctext(d, y0 + 470, f"{n:,}".replace(",", ".") + " FLÜGE GESTRICHEN", font(54), WHITE, stroke=2)
        for i, nm in enumerate(("Router", "Update", "Geräte")):
            tn = word_t("faa", nm)
            if t > tn and t < word_t("faa", "Cyberangriff"):
                lab = ["ROUTER?", "UPDATE?", "ALTGERÄTE?"][i]; s = back((t - tn) / 0.2)
                d.rounded_rectangle([110 + i * 300, y0 + 545, 110 + i * 300 + int(270 * s), y0 + 595], 12, fill=(40, 40, 52))
                d.text((125 + i * 300, y0 + 550), lab, font=font(int(34 * s) + 1), fill=YEL)
    elif name == "gem":
        items = [("SHENZHEN", "99 / 117"), ("TRUMP XI PUTIN", "201"), ("DECODE", "36 = 6×6")]
        for i, (kk, vv) in enumerate(items):
            tg = T_GEM[i] - 0.5
            if t < tg: continue
            shown = vv if t > tg + 0.5 else "".join(random.choice("0123456789") if ch.isdigit() else ch for ch in vv)
            d.text((120, y0 + 30 + i * 115), kk, font=font(50), fill=GREY)
            tw = d.textlength(shown, font=font(62)); d.text((960 - tw, y0 + 22 + i * 115), shown, font=font(62), fill=CYAN)
        if t > T_X:
            p = ease((t - T_X) / 0.25)
            d.line([110, y0 + 30, 110 + 850 * p, y0 + 30 + 330 * p], fill=RED, width=12)
            d.line([110, y0 + 360, 110 + 850 * p, y0 + 360 - 330 * p], fill=RED, width=12)
            ctext(d, y0 + 400, "AUSWAHL ≠ ENTSCHLÜSSELUNG", font(54), RED, stroke=2)
        if t > T_REAL: ctext(d, y0 + 480, "ECHT: 161 km/h · 8.000 FLÜGE", font(50), WHITE, stroke=2)
    elif name == "end":
        lines = ["GIPFEL OHNE DICH", "SATELLIT ENTSCHEIDET FRONT", "EIN ROUTER, EIN LAND"]
        for i, s in enumerate(lines):
            if t > T_LINES[i]:
                n = int(min((t - T_LINES[i]) / 0.63, 1) * len(s)); cur = "▌" if n < len(s) and int(t * 8) % 2 else ""
                ctext(d, y0 + 30 + i * 100, s[:n] + cur, font(56), WHITE)
        if t > T_Q:
            s = back((t - T_Q) / 0.3); pul = 0.5 + 0.5 * math.sin(t * 6)
            f = font(int(60 * s)); ctext(d, y0 + 380, "WARUM SO WENIGE", f, (255, int(40 + 60 * pul), 60), stroke=3)
            ctext(d, y0 + 460, "SCHALTER?", font(int(80 * s)), (255, int(40 + 60 * pul), 60), stroke=3)
    elif name == "cta":
        if t > T_PRUEF:
            s = 1 + 1.5 * (1 - ease((t - T_PRUEF) / 0.18))
            st = Image.new("RGBA", (800, 190)); sd = ImageDraw.Draw(st)
            sd.rounded_rectangle([6, 6, 794, 184], 20, outline=RED, width=12)
            sd.text(((800 - sd.textlength("PRÜF MICH.", font=font(120))) / 2, 22), "PRÜF MICH.", font=font(120), fill=RED)
            st = st.rotate(-4, expand=True, resample=Image.BICUBIC); st = st.resize((int(st.width * s), int(st.height * s)))
            im.alpha_composite(st, (int(W / 2 - st.width / 2), int(y0 + 110 - st.height / 2)))
        ctext(d, y0 + 250, "QUELLEN IN DER BESCHREIBUNG", font(48), WHITE)
        if t > T_FOLLOW:
            s = back((t - T_FOLLOW) / 0.3); pul = 1 + 0.05 * math.sin(t * 8)
            bw, bh = int(420 * s * pul), int(110 * s * pul); bx, by = W // 2 - bw // 2, y0 + 340
            d.rounded_rectangle([bx, by, bx + bw, by + bh], 55, fill=RED if t < T_FOLLOW + 0.6 else (60, 60, 70))
            lab = "+ FOLGEN" if t < T_FOLLOW + 0.6 else "✓ GEFOLGT"
            f = font(max(8, int(54 * s))); fw = d.textlength(lab, font=f); d.text((W / 2 - fw / 2, by + bh / 2 - f.size / 2 - 4), lab, font=f, fill=WHITE)
            hx = W // 2 + 120 - (0 if t > T_FOLLOW + 0.6 else int(40 * (1 - ease((t - T_FOLLOW) / 0.6)))); hy = by + 80
            d.polygon([(hx, hy), (hx + 16, hy + 60), (hx + 30, hy + 42), (hx + 52, hy + 70), (hx + 62, hy + 60), (hx + 40, hy + 34), (hx + 62, hy + 28)], fill=WHITE, outline=(0, 0, 0))
    return im

CHUNKS = []   # caption groups of words
cur = []
for wd in words:
    if cur and (len(cur) >= 3 or cur[-1][4] != wd[4] or cur[-1][2][-1] in ".?!:"):
        CHUNKS.append(cur); cur = []
    cur.append(wd)
CHUNKS.append(cur)

def caption(d, t):
    for g in CHUNKS:
        if g[0][0] <= t < g[-1][1] + 0.05:
            f = font(74); sp = d.textlength(" ", font=f)
            tot = sum(d.textlength(w[2], font=f) for w in g) + sp * (len(g) - 1)
            if tot > W - 100: f = font(int(74 * (W - 100) / tot)); sp = d.textlength(" ", font=f); tot = sum(d.textlength(w[2], font=f) for w in g) + sp * (len(g) - 1)
            x = (W - tot) / 2; y = 1660
            s = back((t - g[0][0]) / 0.15)
            d.rounded_rectangle([x - 28, y - 18, x + tot + 28, y + f.size + 26], 22, fill=(0, 0, 0, 230))
            for w in g:
                col = RED if w[3] else (YEL if w[0] <= t < w[1] else WHITE)
                d.text((x, y + (1 - s) * 30), w[2], font=f, fill=col, stroke_width=3, stroke_fill=(0, 0, 0)); x += d.textlength(w[2], font=f) + sp
            return

def glitch(arr, amt):
    out = arr.copy(); s = int(18 * amt) + 2
    out[:, :, 0] = np.roll(arr[:, :, 0], s, axis=1); out[:, :, 2] = np.roll(arr[:, :, 2], -s, axis=1)
    for _ in range(int(10 * amt)):
        y = random.randint(0, arr.shape[0] - 60); h = random.randint(8, 60); out[y:y + h] = np.roll(out[y:y + h], random.randint(-80, 80), axis=1)
    return out

# --------------------------------------------------------------------------- render
_tick = "  +++  SHENZHEN 19.11.  +++  STARLINK-LIMIT 161 KM/H  +++  8.000 FLÜGE GESTRICHEN  +++  QUELLEN: CNN · CBS · AL JAZEERA · UKRAINSKA PRAVDA · SCMP"
TICK_W = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(_tick, font=font(30)))
TICK_IMG = Image.new("RGB", (TICK_W * 2 + W, 48), (232, 38, 52)); _td = ImageDraw.Draw(TICK_IMG)
for _k in range(3): _td.text((_k * TICK_W, 6), _tick, font=font(30), fill=WHITE)
mlev = 0.0
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-i", f"{WORK}/mix.wav", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                       "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100", "-c:a", "aac", "-b:a", "192k", "-shortest", OUT], stdin=subprocess.PIPE)
for fi in range(NF):
    t = fi / FPS; sc = current_scene(t)
    frame = Image.new("RGB", (W, H), BG)
    frame.paste(render_top(t, fi), (0, 0))
    d = ImageDraw.Draw(frame, "RGBA")
    d.rectangle([0, TOP, W, TOP + 10], fill=RED)
    # top bar
    d.rectangle([0, 0, W, 105], fill=(0, 0, 0, 235))
    if int(t * 1.5) % 2 == 0: d.ellipse([40, 38, 66, 64], fill=RED)
    d.text((82, 28), "LIVE · DER DECODER", font=font(44), fill=WHITE)
    lab = "KI-GENERIERT"; d.text((W - 40 - d.textlength(lab, font=font(32, False)), 38), lab, font=font(32, False), fill=GREY)
    # lower third ticker
    off = int((t * 140) % TICK_W); frame.paste(TICK_IMG.crop((off, 0, off + W, 48)), (0, H - 100))
    # panel with slide-in
    pn = panel(t, sc); lt = t - sc[1]
    ox = int((1 - ease(lt / 0.35)) * W) if sc[0] != "hook" else 0
    frame.paste(pn, (ox, TOP + 30), pn)
    caption(ImageDraw.Draw(frame, "RGBA"), t)
    d = ImageDraw.Draw(frame, "RGBA")
    d.rectangle([0, H - 12, int(W * t / TOTAL), H], fill=RED)
    # flash
    for e in recent("flash", t, 0.15):
        a = int(170 * (1 - (t - e[0]) / 0.15)); d.rectangle([0, 0, W, H], fill=(255, 255, 255, a))
    arr = np.asarray(frame)
    g = recent("glitch", t, 0.4)
    if any(t - e[0] < e[2] for e in g): arr = glitch(arr, 1.0)
    sh = recent("shake", t, 0.35)
    if sh:
        amp = max(e[2] * (1 - (t - e[0]) / 0.35) for e in sh) * 22
        arr = np.roll(arr, (int(random.uniform(-amp, amp)), int(random.uniform(-amp, amp))), axis=(0, 1))
    ff.stdin.write(np.ascontiguousarray(arr).tobytes())
ff.stdin.close(); ff.wait()
print(f"done {OUT} {TOTAL:.1f}s")
