#!/usr/bin/env python3
"""End-to-end test: real video download through the app's engine (no UI needed)."""
import types, time, threading, json
dd = types.ModuleType('dd')
exec(open('duel-downloader.py').read().split('if __name__')[0], dd.__dict__)
from pathlib import Path
import tempfile

tmp = Path(tempfile.mkdtemp())

class Cfg:
    home = tmp
    download_dir = tmp / "Downloads"
    config_file = tmp / ".cfg.json"
    history_file = tmp / ".hist.json"
    web_host = "127.0.0.1"
    web_port = 7777
    web_enabled = True
    data = {
        "theme": "dark", "default_format": "best", "max_concurrent": 2,
        "web_port": 7777, "web_host": "127.0.0.1", "auto_open_browser": False,
        "video_sites": ["youtube.com", "youtu.be", "facebook.com", "fb.watch",
                        "instagram.com", "tiktok.com", "twitter.com", "x.com",
                        "vimeo.com", "dailymotion.com", "twitch.tv", "test-videos.co.uk"],
        "download_dir": str(download_dir),
    }
    def save(self): return True
    def load_config(self): pass

Cfg.download_dir.mkdir(exist_ok=True)
cfg = Cfg()

engine = dd.DownloadEngine(cfg)

print("=" * 60)
print("TEST 1: type detection")
for url in ["https://www.youtube.com/watch?v=video123",
            "https://cdn.example.com/file.pdf",
            "https://ia800309.us.archive.org/31/items/PB109B/pb109b.mp4"]:
    t = engine.detect_type(url)
    print(f"  {url[:60]:60s} -> {t}")

print("=" * 60)
print("TEST 2: video info via yt_dlp (small public video from archive.org)")
url = "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
info = engine.get_video_info(url)
if 'error' in info:
    print("  ERROR:", info['error'])
else:
    print(f"  Title: {info['title'][:60]}")
    print(f"  Uploader: {info['uploader']}")
    print(f"  Duration: {info['duration']}s")
    print(f"  Formats: {len(info['formats'])}")

print("=" * 60)
print("TEST 3: actual video download (best format)")
did = engine.download_video(url, 'best')
print(f"  Download ID: {did}")
for i in range(90):
    time.sleep(2)
    with engine._lock:
        v = dict(engine.active_downloads.get(did, {}))
    status = v.get('status')
    if status in ('completed', 'failed'):
        break
    print(f"  progress={v.get('progress', 0):.0f}% speed={v.get('speed')} eta={v.get('eta')}")
print(f"  FINAL STATUS: {v.get('status')}")
if v.get('status') == 'failed':
    print(f"  ERROR: {v.get('error')}")
else:
    print(f"  File: {v.get('filename')}")
    print(f"  Size: {v.get('filesize', 0) / 1048576:.2f} MB")

print("=" * 60)
print("TEST 4: direct file download (mp4 URL via requests path)")
did2 = engine.download_file(url, download_id=f"filetest_{int(time.time())}")
for i in range(60):
    time.sleep(1)
    with engine._lock:
        v2 = dict(engine.active_downloads.get(did2, {}))
    if v2.get('status') in ('completed', 'failed'):
        break
print(f"  FILE DOWNLOAD STATUS: {v2.get('status')}")
if v2.get('status') == 'failed':
    print(f"  ERROR: {v2.get('error')}")
else:
    print(f"  File: {v2.get('filename')}")

print("=" * 60)
print("TEST 5: history")
for h in engine.history[-3:]:
    print(f"  {h['timestamp'][:19]} | {h['type']:5s} | {h['status']} | {h['filename'][:40]} | {h['size']/1048576:.2f}MB")

# cleanup temp
import shutil
shutil.rmtree(tmp, ignore_errors=True)
print("\nDONE")
