#!/usr/bin/env python3
"""Set and verify 20 topics on the downloader repo using the gh CLI."""
import json
import subprocess

TOPICS = [
    "downloader", "video-downloader", "audio-downloader", "youtube-downloader",
    "yt-dlp", "media-downloader", "file-downloader", "python", "flask",
    "web-interface", "terminal-ui", "python3", "youtube-dl", "mp3", "youtube",
    "instagram-downloader", "tiktok-downloader", "facebook-downloader",
    "cross-platform", "command-line",
]

def gh(args, check=True):
    r = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"gh failed: {r.stderr[:500]}")
    return r.stdout

# PUT topics
payload = json.dumps({"names": TOPICS}).encode()
r = subprocess.run(
    ["gh", "api", "repos/Quincunx33/downloader/topics", "--method", "PUT"],
    input=payload.decode(), capture_output=True, text=True,
)
if r.returncode != 0:
    raise SystemExit(f"PUT failed ({r.returncode}): {r.stderr[:800]}")

# GET to verify
out = gh(["api", "repos/Quincunx33/downloader/topics", "-q", ".names[]"])
names = [n for n in out.splitlines() if n.strip()]
print(f"SUCCESS: {len(names)} topics set")
for n in names:
    print(" -", n)
if len(names) != 20:
    raise SystemExit("Topic count mismatch!")
