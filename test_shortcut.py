#!/usr/bin/env python3
"""Shortcut CLI test: runs the app's main() with fake argv to exercise the shortcut paths."""
import types, sys, os, time, subprocess, shutil
from pathlib import Path

BASE = Path(__file__).parent

def run_test(name, args, expect_in=None):
    p = subprocess.run(
        ['python3', 'duel-downloader.py'] + args,
        cwd=BASE, capture_output=True, text=True, timeout=120,
        env={**os.environ},
    )
    out = p.stdout + p.stderr
    ok = (p.returncode == 0) and all(e.lower() in out.lower() for e in (expect_in or []))
    print(f"{'PASS' if ok else 'FAIL'}: {name} (rc={p.returncode})")
    if not ok:
        print("  stdout+stderr tail:")
        for line in out.splitlines()[-15:]:
            print("   ", line)
    return ok

results = []

# Test 1: --help prints shortcut guide
results.append(run_test("--help", ['--help'], ["Quick shortcuts", "audio"]))

# Test 2: URL-only shortcut -> direct mp4 URL downloads through file path
results.append(run_test(
    "URL-only (best)",
    ['https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4'],
    ['Quick download', 'Download started', 'Download completed']
))

# Clean up downloaded test files
dl = BASE / 'Downloads'
for f in dl.glob('*Big_Buck_Bunny*'):
    f.unlink()

passed = sum(results)
print(f"\n{passed}/{len(results)} tests passed")
sys.exit(0 if passed == len(results) else 1)
