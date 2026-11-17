#!/usr/bin/env python3
"""Minimal HeyGen Voice 1 text-to-speech request.

POST https://api.heygen.com/v3/models/audio/tts is synchronous: the request stays
open until the audio file is ready, then returns its `audio_url` (no status endpoint
to poll). This script waits for that response and retries only when HeyGen asks it
to (429 rate limit / 5xx), honouring Retry-After, then prints the output URL.

Auth: X-Api-Key from the HEYGEN_API_KEY environment variable.
Usage: python3 heygen_tts.py ["text"] [--model heygen-voice-1|heygen-voice-1-turbo|heygen-voice-1-turbo-free]
"""
import json, os, sys, time, urllib.error, urllib.request

URL = "https://api.heygen.com/v3/models/audio/tts"
VOICE_ID = "be8d7bf8ce774bda8b6dd04541fb8623"   # "Florian - Dynamic & Punchy" (public, German)
TEXT = "Hallo, hier ist der Decoder. Prüf mich."
MODEL = "heygen-voice-1"

args = sys.argv[1:]
if "--model" in args:
    i = args.index("--model"); MODEL = args[i + 1]; del args[i:i + 2]
if args: TEXT = args[0]

key = os.environ.get("HEYGEN_API_KEY")
if not key:
    sys.exit("HEYGEN_API_KEY is not set. Create a key at https://platform.heygen.com/api-keys "
             "and export it yourself:  export HEYGEN_API_KEY=...   (never paste it into a chat)")

body = {
    "model": MODEL,
    "voice_id": VOICE_ID,
    "text": TEXT,
    "language": "de",
    # cheapest/smallest output: mono MP3, lowest sample rate + bitrate the API allows
    "output_format": {"encoding": "mp3", "sample_rate_hertz": 22050, "bitrate_bps": 32000},
}
print(f"model={MODEL} voice={VOICE_ID} chars={len(TEXT)}", file=sys.stderr)

for attempt in range(1, 7):
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST",
                                 headers={"X-Api-Key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.load(r); hdr = r.headers
        d = data.get("data", data)
        print(f"done: duration={d.get('duration')}s language={hdr.get('Content-Language')} "
              f"request_id={hdr.get('X-Request-Id')}", file=sys.stderr)
        print(d["audio_url"])
        break
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")
        if e.code == 429 or e.code >= 500:
            wait = int(e.headers.get("Retry-After") or 2 ** attempt)
            print(f"attempt {attempt}: HTTP {e.code}, retrying in {wait}s", file=sys.stderr)
            time.sleep(wait); continue
        sys.exit(f"HTTP {e.code}: {err}")
else:
    sys.exit("gave up after 6 attempts")
