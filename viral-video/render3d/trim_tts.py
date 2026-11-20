"""Cut sentences out of cached ElevenLabs TTS (with-timestamps) without new API calls.
usage: python3 trim_tts.py src_workdir dst_workdir episode.json [tempo]
For each scene i, the episode text (spoken form) must consist of sentences/phrases that appear
verbatim, in order, in the source cache tts_XX_<scene>.json. Writes matching caches into dst."""
import base64, json, os, re, subprocess, sys, glob
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
SR = 44100
src, dst, ep = sys.argv[1:4]; tempo = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
os.makedirs(dst, exist_ok=True)

def spoken_of(text):  # same rules as make_audio.parse
    out = ""
    for m in re.finditer(r"\*?\{([^|}]*)\|([^}]*)\}\*?|\S+|\s+", text):
        s = m.group(0)
        if s.isspace(): out += " "; continue
        out += m.group(2) if m.group(1) is not None else s.replace("*", "")
    return out

def dec(b64):
    p = f"{dst}/_in.mp3"; open(p, "wb").write(base64.b64decode(b64))
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

scenes = json.load(open(ep))["scenes"]
for i, (sc, text) in enumerate(scenes):
    srcf = glob.glob(f"{src}/tts_*_{sc}.json")[0]
    r = json.load(open(srcf)); al = r["alignment"]
    C = "".join(al["characters"]); st, en = al["character_start_times_seconds"], al["character_end_times_seconds"]
    a = dec(r["audio_base64"])
    target = spoken_of(text)
    # split target into phrases separated by the sentence boundaries; greedily match maximal runs in C
    parts, pos, k = [], 0, 0
    while k < len(target):
        # longest prefix of target[k:] found in C at/after pos
        lo, best = k + 1, None
        for e in range(len(target), k, -1):
            if target[e - 1] == " ": continue
            j = C.find(target[k:e], pos)
            if j >= 0: best = (j, e); break
        assert best, (sc, target[k:k + 40])
        j, e = best; parts.append((j, j + (e - k))); pos = j + (e - k); k = e
        while k < len(target) and target[k] == " ": k += 1
    out, chars, s0, e0, t = [], [], [], [], 0.0
    gap = 0.22
    for n, (cs, ce) in enumerate(parts):
        a0 = max(0.0, st[cs] - 0.04 if cs else 0.0); a1 = min(len(a) / SR, en[ce - 1] + 0.14)
        if ce == len(C): a1 = len(a) / SR
        if n:
            out.append(np.zeros(int(SR * gap), np.float32)); chars.append(" "); s0.append(t); e0.append(t + gap); t += gap
        seg = a[int(a0 * SR):int(a1 * SR)]
        # tiny fades against clicks
        f = min(len(seg) // 2, int(SR * 0.012)); seg = seg.copy(); seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
        out.append(seg)
        for c in range(cs, ce): chars.append(C[c]); s0.append(t + st[c] - a0); e0.append(t + en[c] - a0)
        t += len(seg) / SR
    y = np.concatenate(out)
    assert "".join(chars) == target, (sc, "".join(chars), target)
    wav = f"{dst}/_o.wav"
    import wave
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    mp3 = f"{dst}/_o.mp3"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-af", f"atempo={tempo}", "-b:a", "128k", mp3], check=True)
    s0 = [x / tempo for x in s0]; e0 = [x / tempo for x in e0]
    alg = {"characters": chars, "character_start_times_seconds": s0, "character_end_times_seconds": e0}
    json.dump({"audio_base64": base64.b64encode(open(mp3, "rb").read()).decode(), "alignment": alg, "normalized_alignment": alg},
              open(f"{dst}/tts_{i:02d}_{sc}.json", "w"))
    print(sc, f"{len(y) / SR / tempo:.1f}s", len(parts), "parts")
for f in ("_in.mp3", "_o.wav", "_o.mp3"):
    try: os.remove(f"{dst}/{f}")
    except OSError: pass
