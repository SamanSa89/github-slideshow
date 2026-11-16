"""Episode 02 audio: ElevenLabs voice (word timings) + subtle music bed + minimal SFX.

Markup in SCRIPT:  *word* = highlight,  {Shown text|spoken text} = caption differs from speech.
usage: python3 make_audio.py workdir [voice_id]
"""
import base64, json, os, re, subprocess, sys, urllib.request, wave
import numpy as np

WORK = sys.argv[1] if len(sys.argv) > 1 else "work"
VOICE = sys.argv[2] if len(sys.argv) > 2 else "nPczCjzI2devNBz1zQrb"   # "Brian" premade
os.makedirs(WORK, exist_ok=True)
SR, FPS = 44100, 30

SCRIPT = [
 ("hook", "{48 Stunden.|Achtundvierzig Stunden.} Ein Raumschiff wird mit *Stäbchen* aus dem All gefangen. Und der größte Rivale verliert *{40 Satelliten|vierzig Satelliten}* in zehn Minuten. Du denkst, das ist Nerdkram aus dem Weltraum? Nein. Hier geht es darum, wem der *Himmel* über dir gehört."),
 ("starship", "Freitag, Texas. SpaceX fängt zum ersten Mal ein Starship, das aus dem *Orbit* zurückkommt, mit den Armen des Startturms, nach über {22 Stunden|zweiundzwanzig Stunden} im All. Vorher setzt es {26|sechsundzwanzig} neue Starlink-Satelliten aus. Der Booster landet diesmal im Meer. Aber das Signal ist eindeutig."),
 ("vulcan", "Einen Tag später, Florida. Die Vulcan-Rakete von ULA, der Firma von Boeing und Lockheed, soll die ersten {40|vierzig} Satelliten für Amazon Leo ins All bringen. Zehn Minuten nach dem Start: *Anomalie.* Alle {40|vierzig}: verloren. Amazon hat damit knapp {400|vierhundert} Satelliten im Orbit. Gebraucht werden über {3.200.|dreitausendzweihundert.}"),
 ("connect", "Jetzt verbinde die Punkte. Wer Satelliten hat, hat Internet. Und wer das Internet hat, *entscheidet.* Das haben wir in der Ukraine gesehen, wo Starlink ab {161 km/h|hunderteinundsechzig Kilometern pro Stunde} abschaltet. Europa sucht deshalb nach einer Alternative. Und der größte Herausforderer ist gerade gescheitert."),
 ("genf", "Und während der Himmel verteilt wird, verhandeln heute in *Genf* Vertreter aus {128|hundertachtundzwanzig} Staaten über Killerroboter. Waffen, die selbst entscheiden, wen sie treffen. Berichten zufolge wollen ausgerechnet die USA und Russland die menschliche Kontrolle aus dem Text streichen. Bestätigt ist das *nicht.* Aber wenn es stimmt, ist das die eigentliche Schlagzeile des Tages."),
 ("verdict", "Ist das eine Verschwörung? Nein. Das ist Physik und Geld. Wer zuverlässig in den Orbit kommt, kontrolliert die Infrastruktur dieses Jahrhunderts. Und gerade sieht es so aus, als hielte im Westen nur *eine Firma* diesen Schlüssel wirklich in der Hand."),
 ("cta", "Also: Glaub mir nicht. *Prüf mich.* Die Quellen stehen in der Beschreibung. Ich bin der Decoder. Folg mir, morgen geht es weiter."),
]

def parse(text):
    """-> spoken string, tokens [(display, hl, span_start, span_end)] (spans in spoken string)."""
    spoken, toks = "", []
    for m in re.finditer(r"\*?\{([^|}]*)\|([^}]*)\}\*?|\S+|\s+", text):
        s = m.group(0)
        if s.isspace(): spoken += " "; continue
        hl = s.startswith("*") or s.endswith("*") or s.rstrip(".,:?!").endswith("*")
        if m.group(1) is not None:
            disp, spk = m.group(1), m.group(2)
        else:
            disp = s.replace("*", ""); spk = disp
        a = len(spoken); spoken += spk
        toks.append((disp, hl, a, len(spoken)))
    return spoken, toks

def tts(text, prev, nxt):
    body = {"text": text, "model_id": "eleven_multilingual_v2", "previous_text": prev, "next_text": nxt,
            "voice_settings": {"stability": 0.42, "similarity_boost": 0.8, "style": 0.32, "use_speaker_boost": True}}
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_128",
                                 data=json.dumps(body).encode(), headers={"xi-api-key": "proxy-injected", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=180))

def mp3_to_np(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

parsed = [(sc, *parse(tx)) for sc, tx in SCRIPT]
voice_parts, words, scenes, t = [np.zeros(int(SR * 0.6), np.float32)], [], [], 0.6
for i, (sc, spoken, toks) in enumerate(parsed):
    cache = f"{WORK}/tts_{i:02d}_{sc}.json"
    if os.path.exists(cache):
        r = json.load(open(cache))
    else:
        r = tts(spoken, parsed[i - 1][1] if i else "", parsed[i + 1][1] if i + 1 < len(parsed) else "")
        json.dump(r, open(cache, "w"))
    open(f"{WORK}/tmp.mp3", "wb").write(base64.b64decode(r["audio_base64"]))
    a = mp3_to_np(f"{WORK}/tmp.mp3")
    al = r["alignment"]; st, en = al["character_start_times_seconds"], al["character_end_times_seconds"]
    if "".join(al["characters"]) != spoken: print("warn: alignment text differs for", sc)
    scenes.append({"name": sc, "start": t, "end": t + len(a) / SR})
    for disp, hl, s0, s1 in toks:
        s1c = min(s1, len(st)) - 1; s0c = min(s0, len(st) - 1)
        words.append({"t0": t + st[s0c], "t1": t + en[max(s1c, s0c)], "w": disp, "hl": hl, "scene": sc})
    voice_parts += [a, np.zeros(int(SR * 0.45), np.float32)]; t += len(a) / SR + 0.45
voice_parts.append(np.zeros(int(SR * 1.5), np.float32)); t += 1.5
TOTAL = t; N = int(TOTAL * SR)
V = np.concatenate(voice_parts)[:N]; V = np.pad(V, (0, N - len(V)))

# light voice polish
def wav_write(p, x):
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
def wav_read(p):
    with wave.open(p) as w: return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
wav_write(f"{WORK}/voice_raw.wav", V)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{WORK}/voice_raw.wav", "-af",
                "highpass=f=70,equalizer=f=120:t=q:w=1:g=2,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=120:makeup=2", f"{WORK}/voice.wav"], check=True)
V = wav_read(f"{WORK}/voice.wav"); V = np.pad(V, (0, max(0, N - len(V))))[:N]

# ---- subtle music: dark pad + soft half-time pulse
rng = np.random.default_rng(3)
tt = lambda d: np.arange(int(d * SR)) / SR
MUS, FX = np.zeros(N), np.zeros(N)
def add(buf, x, at, g=1.0):
    i = int(at * SR)
    if i < 0: x = x[-i:]; i = 0
    x = x[:max(0, N - i)]; buf[i:i + len(x)] += x * g
bpm = 84; bar = 4 * 60 / bpm
chords = [(110.0, 130.81, 164.81), (87.31, 110.0, 130.81), (130.81, 164.81, 196.0), (98.0, 123.47, 146.83)]
k_t = tt(0.6); kick = np.sin(2 * np.pi * np.cumsum(42 + 60 * np.exp(-k_t * 25)) / SR) * np.exp(-k_t * 6)
b, i = 0.3, 0
while b < TOTAL:
    x = tt(bar); ch = chords[i % 4]
    pad = sum(np.sin(2 * np.pi * f * x + 0.4 * np.sin(2 * np.pi * 0.25 * x + j)) for j, f in enumerate(ch)) / 3
    pad *= np.minimum(1, x / 0.8) * np.minimum(1, (bar - x) / 0.8)
    add(MUS, pad, b, 0.35)
    sub = np.sin(2 * np.pi * ch[0] / 2 * x) * np.exp(-x * 0.6); add(MUS, sub, b, 0.25)
    for beat in (0, 2.5):
        if b > 6: add(MUS, kick, b + beat * bar / 4, 0.45)
    b += bar; i += 1
env = np.convolve(np.abs(V), np.ones(4410) / 4410, mode="same")
MUS *= 1 - 0.6 * np.clip(env / (env.max() * 0.3), 0, 1)
fade = np.ones(N); fl = int(2.5 * SR); fade[-fl:] = np.linspace(1, 0, fl); MUS *= fade

# ---- minimal SFX
def whoosh(d=0.7):
    x = rng.uniform(-1, 1, int(d * SR)); y = np.empty_like(x); z = 0
    for k in range(len(x)):
        fc = 200 + 3500 * np.sin(np.pi * k / len(x)); a = np.exp(-2 * np.pi * fc / SR); z = (1 - a) * x[k] + a * z; y[k] = z
    return y * np.sin(np.pi * np.arange(len(x)) / len(x)) ** 2 * 1.5
def boom():
    x = tt(2.0); return np.tanh(1.5 * np.sin(2 * np.pi * np.cumsum(30 + 50 * np.exp(-x * 8)) / SR) * np.exp(-x * 1.8))
def riser(d=1.6):
    x = tt(d); return np.sin(2 * np.pi * np.cumsum(150 + 900 * (x / d) ** 2) / SR) * (x / d) ** 2.5
W_ = whoosh()
for s in scenes[1:]: add(FX, W_, s["start"] - 0.5, 0.35)
add(FX, boom(), scenes[0]["start"], 0.55)
anom = next(w["t0"] for w in words if w["scene"] == "vulcan" and w["w"].startswith("Anomalie"))
add(FX, boom(), anom, 0.6)
vs = next(s for s in scenes if s["name"] == "verdict")["start"]; add(FX, riser(), vs - 1.6, 0.25)
pm = next(w["t0"] for w in words if w["scene"] == "cta" and w["w"].startswith("Prüf")); add(FX, boom(), pm, 0.35)

MIX = V + MUS * 0.16 + FX * 0.5
MIX = MIX / (np.abs(MIX).max() + 1e-6) * 0.95
wav_write(f"{WORK}/mix.wav", MIX)

hop = SR // FPS; nf = int(TOTAL * FPS) + 1
lev = np.array([np.sqrt(np.mean(V[k * hop:(k + 1) * hop] ** 2)) if k * hop < N else 0 for k in range(nf)])
lev = np.clip(lev / (np.percentile(lev[lev > 0.003], 95) + 1e-6), 0, 1)
json.dump({"total": TOTAL, "fps": FPS, "scenes": scenes, "words": words, "mouth": [round(float(x), 3) for x in lev],
           "events": {"anomaly": anom, "pruef": pm}}, open(f"{WORK}/timeline.json", "w"), ensure_ascii=False)
print(f"total {TOTAL:.1f}s, words {len(words)}, chars {sum(len(p[1]) for p in parsed)}")
