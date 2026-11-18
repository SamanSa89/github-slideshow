"""Marker-on-paper sound effects driven by the Leinwand pen log, mixed into an episode mix.

usage: python3 pen_sfx.py pen.json workdir   (reads workdir/mix.wav, keeps a copy as mix_base.wav, writes new mix.wav)
pen.json: [[t, null | {x, y, k: 'draw'|'write'}], ...] one entry per video frame
"""
import json, os, shutil, sys, wave
import numpy as np

PEN, WORK = sys.argv[1], sys.argv[2]
SR = 44100
log = json.load(open(PEN))
base = f"{WORK}/mix_base.wav"
if not os.path.exists(base): shutil.copy(f"{WORK}/mix.wav", base)
with wave.open(base) as w:
    mix = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
N = len(mix); rng = np.random.default_rng(11)

def band(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.clip((f - lo * 0.7) / (lo * 0.3), 0, 1) * np.clip((hi * 1.3 - f) / (hi * 0.3), 0, 1)
    return np.fft.irfft(X * g, len(x))

# per-frame envelopes (speed driven) for drawing and writing
fps = 1 / (log[1][0] - log[0][0]) if len(log) > 1 else 30
env_d = np.zeros(len(log)); env_w = np.zeros(len(log)); taps = []
prev = None
for i, (t, p) in enumerate(log):
    if p:
        sp = 0.0 if prev is None else np.hypot(p["x"] - prev["x"], p["y"] - prev["y"])
        lvl = np.clip(sp / 25.0, 0.25, 1.0)
        (env_w if p["k"] == "write" else env_d)[i] = lvl
        if prev is None: taps.append(t)
    prev = p
def to_samples(env):
    x = np.interp(np.arange(N) / SR * fps, np.arange(len(env)), env, right=0)
    k = int(0.03 * SR); return np.convolve(x, np.ones(k) / k, mode="same")
ed, ew = to_samples(env_d), to_samples(env_w)

noise = rng.standard_normal(N).astype(np.float32)
grain = np.repeat(rng.uniform(0.4, 1.0, N // 600 + 1), 600)[:N]                     # paper fibre grain (~70 Hz)
scratch = band(noise, 1800, 6500) * grain                                            # felt tip on paper
tsec = np.arange(N) / SR
squeak = band(noise, 2200, 3800) * (0.55 + 0.45 * np.sin(2 * np.pi * 9 * tsec) ** 2)  # handwriting: rhythmic strokes
pen = scratch * ed * 0.9 + squeak * ew * 0.75
for t in taps:                                                                         # pen touches paper
    i = int(t * SR); L = int(0.03 * SR)
    if i + L < N: pen[i:i + L] += band(rng.standard_normal(L), 600, 3000) * np.exp(-np.arange(L) / (0.006 * SR)) * 1.5
pen /= (np.abs(pen).max() + 1e-6)

# keep it under the voice: about -24 dB relative to the mix peak, ducked a little more while speaking
venv = np.convolve(np.abs(mix), np.ones(2205) / 2205, mode="same")
duck = 1 - 0.45 * np.clip(venv / (venv.max() * 0.3), 0, 1)
out = mix + pen * 0.12 * duck
out = out / max(1.0, np.abs(out).max() / 0.97)
with wave.open(f"{WORK}/mix.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype(np.int16).tobytes())
rms = lambda x: 20 * np.log10(np.sqrt(np.mean(x[x != 0] ** 2)) + 1e-9)
print(f"pen active {np.mean((ed + ew) > 0.01) * 100:.0f}% of time, taps {len(taps)}, pen level {rms(pen * 0.12):.1f} dBFS vs mix {rms(mix):.1f} dBFS")
