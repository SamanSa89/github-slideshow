"""Hybrid anchor: keep body, gestures, head motion, eyes and brows from an existing (paid) HeyGen green-screen video,
replace only the mouth/chin region with our own lip-synced mouth driven by a new voice track.

usage: python3 hybrid_anchor.py heygen.mp4 green916.png anchor.png mask.png workdir face_landmarker.task out.mp4 [still_frame]
- green916.png: the exact image HeyGen animated (anchor on #00B140, 1000 px wide, bottom aligned)
- workdir/timeline.json: new episode timeline (mouth levels per frame, fps, total)
"""
import json, math, os, subprocess, sys
import cv2, numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

HG, G916, A_PNG, M_PNG, WORK, TASK, OUT = sys.argv[1:8]
STILL = int(sys.argv[8]) if len(sys.argv) > 8 else None
TL = json.load(open(f"{WORK}/timeline.json")); FPS = TL["fps"]; NF = int(TL["total"] * FPS)
W, H = 1080, 1920

# ---- reuse the mouth model from anchor_compose.py (closed lips at rest, single opening)
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "anchor_compose.py")).read()
src = src.split("# ------------------------------------------------------------------ timing helpers")[0]
ns = {"__name__": "anchor_model", "clamp": lambda x, a=0.0, b=1.0: max(a, min(b, x))}
sys_argv = sys.argv; sys.argv = ["x", A_PNG, M_PNG, "-", WORK, "-"]
exec(compile(src, "anchor_compose_model", "exec"), ns); sys.argv = sys_argv
animate_head, PERSON = ns["animate_head"], ns["PERSON"]
BX0, BY0 = ns["BX0"], ns["BY0"]

# geometry of green916 (same recipe as when it was made)
img = cv2.cvtColor(cv2.imread(A_PNG), cv2.COLOR_BGR2RGB); m0 = cv2.imread(M_PNG, 0)
ys, xs = np.where(m0 > 20); gx0, gx1, gy0 = xs.min(), xs.max(), ys.min()
gw = gx1 + 1 - gx0; s0 = 1000 / gw; gh = int(round((img.shape[0] - gy0) * s0)); gox, goy = (W - 1000) // 2, H - gh

def mouth_frame(a):
    """Full 1080x1920 RGB frame of the photo (green bg) with our mouth at opening a."""
    p = animate_head(a, 0.0, 0.0, 0.0, 0.0)                       # RGBA in PERSON coords
    sub = p[gy0 - BY0:, gx0 - BX0:gx1 + 1 - BX0]
    sub = cv2.resize(sub, (1000, gh), interpolation=cv2.INTER_AREA)
    fr = np.zeros((H, W, 3), np.float32); fr[:] = (0, 177, 64)
    al = sub[..., 3:4].astype(np.float32) / 255
    fr[goy:goy + gh, gox:gox + 1000] = fr[goy:goy + gh, gox:gox + 1000] * (1 - al) + sub[..., :3] * al
    return fr

LEVELS = np.linspace(0, 1, 13)
CACHE = {}
def mouth_cached(a):
    k = int(round(a * (len(LEVELS) - 1)))
    if k not in CACHE: CACHE[k] = mouth_frame(LEVELS[k])
    return CACHE[k]

# ---- landmarks
def landmarker(mode):
    opts = vision.FaceLandmarkerOptions(base_options=mpt.BaseOptions(model_asset_path=TASK), running_mode=mode, num_faces=1)
    return vision.FaceLandmarker.create_from_options(opts)
def pts(res):
    if not res.face_landmarks: return None
    return np.array([[p.x * W, p.y * H] for p in res.face_landmarks[0]], np.float32)

ref = cv2.cvtColor(cv2.imread(G916), cv2.COLOR_BGR2RGB)
with landmarker(vision.RunningMode.IMAGE) as lm:
    L0 = pts(lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=ref)))
assert L0 is not None, "no face in green916"
STABLE = [33, 133, 362, 263, 168, 6, 197, 1, 4, 234, 454, 127, 356, 10, 98, 327]   # eyes, nose, temples, forehead, nose wings: unaffected by speech
JAW = [58, 172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397, 288]
TOP = [205, 98, 2, 327, 425]
ctr = L0[[13, 14]].mean(0)
jaw = ctr + (L0[JAW] - ctr) * np.array([0.86, 0.95])          # pull the jaw outline inwards -> no background at the edges
poly = np.vstack([L0[TOP], jaw[::-1]])
chin = ctr + (L0[[149, 176, 148, 152, 377, 400, 378]] - ctr) * np.array([0.86, 1.0]) + np.array([0, 16])
MASK0 = np.zeros((H, W), np.uint8)
cv2.fillPoly(MASK0, [cv2.convexHull(np.vstack([poly, chin]).astype(np.int32))], 255)
MASK0 = cv2.GaussianBlur(MASK0, (0, 0), 10).astype(np.float32) / 255
# never take pixels that are background in the photo
pa = cv2.resize(m0[gy0:, gx0:gx1 + 1], (1000, gh), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
PAL = np.zeros((H, W), np.float32); PAL[goy:goy + gh, gox:gox + 1000] = pa
PAL = cv2.GaussianBlur(cv2.erode(PAL, np.ones((15, 15))), (0, 0), 4)
MASK0 = MASK0 * PAL
RING0 = (cv2.dilate((MASK0 > 0.05).astype(np.uint8), np.ones((41, 41))) - (MASK0 > 0.05).astype(np.uint8)).astype(bool)

# ---- frame loop
dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", HG, "-vf", f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = None if STILL is not None else subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                                        "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)
mouth = np.array(TL["mouth"] + [0] * 10); msm = 0.0; lastM = None; lastFrame = None
lm = landmarker(vision.RunningMode.VIDEO)
for fi in range(NF):
    raw = dec.stdout.read(W * H * 3)
    if len(raw) < W * H * 3: frame = lastFrame
    else: frame = np.frombuffer(raw, np.uint8).reshape(H, W, 3); lastFrame = frame
    msm = 0.55 * msm + 0.45 * float(mouth[fi]); a = min(1.0, (msm * 1.15)) ** 0.85
    if STILL is not None and fi < STILL: continue
    Lf = pts(lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(frame)), int(fi * 1000 / FPS)))
    if Lf is not None:
        M, _ = cv2.estimateAffine2D(L0[STABLE], Lf[STABLE], method=cv2.LMEDS)
        if M is not None:
            # match the lower-face width of the live frame (HeyGen narrows the jaw while speaking)
            JW = [58, 288, 172, 397, 136, 365]
            P0 = cv2.transform(L0[JW][None], M)[0]
            w0 = np.mean([np.linalg.norm(P0[i] - P0[i + 1]) for i in (0, 2, 4)])
            wf = np.mean([np.linalg.norm(Lf[JW][i] - Lf[JW][i + 1]) for i in (0, 2, 4)])
            sx = float(np.clip(wf / max(w0, 1), 0.82, 1.08))
            c = Lf[[13, 14]].mean(0)
            S = np.array([[sx, 0, c[0] * (1 - sx)], [0, 1, 0]], np.float32)
            M = (np.vstack([S, [0, 0, 1]]) @ np.vstack([M, [0, 0, 1]]))[:2]
            lastM = M if lastM is None else 0.6 * M + 0.4 * lastM     # light smoothing against jitter
    out = frame.astype(np.float32)
    if lastM is not None:
        patch = cv2.warpAffine(mouth_cached(a), lastM, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        mk = cv2.warpAffine(MASK0, lastM, (W, H), flags=cv2.INTER_LINEAR)[..., None]
        ring = cv2.warpAffine(RING0.astype(np.uint8), lastM, (W, H), flags=cv2.INTER_NEAREST).astype(bool)
        if ring.sum() > 200:                                                          # match colour/brightness to the live frame
            g = (out[ring].mean(0) + 1) / (patch[ring].mean(0) + 1); patch = patch * np.clip(g, 0.85, 1.15)
        out = out * (1 - mk) + patch * mk
    o8 = np.clip(out, 0, 255).astype(np.uint8)
    if STILL is not None:
        cv2.imwrite(OUT, cv2.cvtColor(o8, cv2.COLOR_RGB2BGR)); break
    enc.stdin.write(o8.tobytes())
if enc: enc.stdin.close(); enc.wait()
dec.kill(); print("done", OUT)
