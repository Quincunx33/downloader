#!/usr/bin/env python3
"""Logic test: verify separated video/audio format lists are deduped correctly."""
import types, threading
dd = types.ModuleType('dd')
exec(open('duel-downloader.py').read().split('if __name__')[0], dd.__dict__)
from pathlib import Path
import tempfile, time

tmp = Path(tempfile.mkdtemp())

class Cfg:
    home = tmp
    download_dir = tmp / "Downloads"
    config_file = tmp / ".cfg.json"
    history_file = tmp / ".hist.json"
    web_host = "127.0.0.1"
    web_port = 7777
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
engine = dd.DownloadEngine(Cfg())

results = []
def check(name, cond, detail=""):
    results.append((name, cond, detail))
    print(('PASS' if cond else 'FAIL') + f": {name} {detail}")

# ---- 1. print_format_lists with mocked separated lists ----
info = {
    'title': 'Test Video', 'uploader': 'Tester', 'duration': 120,
    'videos': [
        {'format_id': '137', 'resolution': '1080p', 'ext': 'mp4', 'fps': 30, 'filesize': 50*1024*1024, 'height': 1080},
        {'format_id': '248', 'resolution': '1080p', 'ext': 'webm', 'fps': 30, 'filesize': 45*1024*1024, 'height': 1080},
        {'format_id': '136', 'resolution': '720p', 'ext': 'mp4', 'fps': 30, 'filesize': 25*1024*1024, 'height': 720},
    ],
    'audios': [
        {'format_id': '140', 'abr': 128, 'ext': 'm4a', 'filesize': 2*1024*1024},
        {'format_id': '251', 'abr': 160, 'ext': 'webm', 'filesize': 2.5*1024*1024},
        {'format_id': '140b', 'abr': 128, 'ext': 'm4a', 'filesize': 2*1024*1024},  # duplicate of 140
    ],
}

class TI(dd.TerminalInterface):
    def __init__(self):
        pass

import io, sys
buf = io.StringIO()
old = sys.stdout; sys.stdout = buf
TI().print_format_lists(info)
sys.stdout = old
out = buf.getvalue()
check("Prints Video qualities header", "Video qualities" in out)
check("Prints Audio qualities header", "Audio qualities" in out)
check("Shows 1080p mp4", "1080p" in out)
check("Shows 720p", "720p" in out)
check("Shows 128kbps audio", "128" in out)
check("Shows 160kbps audio", "160" in out)
print("\n--- sample output ---")
print(out[:1200])

# ---- 2. dedupe logic in get_format_lists: replace extract_info with mock ----
mock_info = {
    'title': 'M', 'uploader': 'U', 'duration': 10,
    'formats': [
        # duplicates: same (resolution, ext)
        {'format_id': '1', 'vcodec': 'avc1', 'acodec': 'none', 'resolution': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 1000},
        {'format_id': '2', 'vcodec': 'avc1', 'acodec': 'none', 'resolution': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 1000},
        # audio duplicates: same (abr, ext)
        {'format_id': '3', 'vcodec': 'none', 'acodec': 'mp4a', 'abr': 128, 'ext': 'm4a', 'filesize': 500},
        {'format_id': '4', 'vcodec': 'none', 'acodec': 'mp4a', 'abr': 128, 'ext': 'm4a', 'filesize': 500},
        {'format_id': '5', 'vcodec': 'avc1', 'acodec': 'none', 'resolution': '480p', 'ext': 'mp4', 'height': 480, 'filesize': 500},
    ],
}
with __import__('unittest.mock').mock.patch.object(dd.yt_dlp.YoutubeDL, 'extract_info', return_value=mock_info):
    res = engine.get_format_lists('https://youtube.com/watch?v=x')
check("Dedupe videos: 720p duplicates -> 1 (480p সহ মোট 2)", len(res['videos']) == 2 and sum(1 for v in res['videos'] if v['resolution']=='720p') == 1, f"got {len(res['videos'])}")
check("Dedupe audio: 128k duplicates -> 1", len(res['audios']) == 1, f"got {len(res['audios'])}")
check("480p video present", any(v['resolution'] == '480p' for v in res['videos']))

# ---- 3. format query map includes quality presets ----
dl = dd.DownloadEngine(Cfg())
# inspect the map inside download_video thread won't run; just check source
src = open('duel-downloader.py').read()
for preset in ["'720p'", "'1080p'", "'480p'", "'360p'", "'audio'"]:
    check(f"format map has preset {preset}", preset + ":" in src or preset + "':" in src)

# ---- 4. download_video with audio mode sets bestaudio ----
import shutil
shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{sum(1 for _,ok,_ in results if ok)}/{len(results)} passed")
