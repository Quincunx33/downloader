<div align="center">

<img src="repo-banner.png" alt="Downloader Banner" width="100%">

# ⚡ Duel Downloader

```text
 ██████╗ ██╗   ██╗██╗ ██████╗ ██████╗ ███████╗███████╗
 ██╔══██╗██║   ██║██║██╔═══██╗██╔══██╗██╔════╝██╔════╝
 ██║  ██║██║   ██║██║██║   ██║██████╔╝█████╗  ███████╗
 ██║  ██║╚██╗ ██╔╝██║██║   ██║██╔══██╗██╔══╝  ╚════██║
 ██████╔╝ ╚████╔╝ ██║╚██████╔╝██║  ██║███████╗███████║
 ╚═════╝   ╚═══╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝
```

**A universal media downloader — video, audio, and any file — with a dual Terminal + Web interface.**

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![yt-dlp](https://img.shields.io/badge/Engine-yt--dlp-E76F00?style=for-the-badge&logo=youtubedownload&logoColor=white)](https://github.com/yt-dlp/yt-dlp)
[![Platform](https://img.shields.io/badge/Platform-Android%20%7C%20iOS%20%7C%20Windows%20%7C%20Linux-0B93F5?style=for-the-badge)](https://github.com/Quincunx33/downloader)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

</div>

---

## 🚀 Quick Start

```bash
# Install dependencies
pip3 install flask flask-socketio yt-dlp requests

# Run the tool
python3 duel-downloader.py

# OR — use the lightning-fast shortcut mode
python3 duel-downloader.py <URL>          # list formats + download best
python3 duel-downloader.py <URL> 720p     # download in 720p directly
python3 duel-downloader.py <URL> audio    # audio-only download
```

---

## 📖 Table of Contents

1. [Dual Interface Modes](#1-dual-interface-modes)
2. [One-Line Shortcut Downloads](#2-one-line-shortcut-downloads)
3. [Audio-Only Mode](#3-audio-only-mode)
4. [Separated Quality Lists](#4-separated-quality-lists)
5. [Quality Presets](#5-quality-presets)
6. [Smart URL Type Detection](#6-smart-url-type-detection)
7. [Live Download Progress](#7-live-download-progress)
8. [Speed, ETA & Real-Time Stats](#8-speed-eta--real-time-stats)
9. [Background Downloading](#9-background-downloading)
10. [Concurrent Download Limits](#10-concurrent-download-limits)
11. [Download History](#11-download-history)
12. [File Browser & Manager](#12-file-browser--manager)
13. [Direct File Downloads](#13-direct-file-downloads)
14. [Resilient Resumable Sessions](#14-resilient-resumable-sessions)
15. [Statistics Dashboard](#15-statistics-dashboard)
16. [Thread-Safe Architecture](#16-thread-safe-architecture)
17. [Security Hardening](#17-security-hardening)
18. [Cross-Platform Compatibility](#18-cross-platform-compatibility)
19. [LAN Access — Share With Any Device](#19-lan-access--share-with-any-device)
20. [Persistent Settings & Config](#20-persistent-settings--config)

---

## Features in Detail

### 1. Dual Interface Modes

Run it your way — a classic **Terminal UI** with an interactive menu, a modern **Web UI** in your browser, or **both at the same time**. One engine powers both interfaces.

### 2. One-Line Shortcut Downloads

No menus needed. Pass a URL as a command-line argument and the tool detects, lists, and downloads in a single command — with a live progress bar and a clear `🎉 Download completed` finish message.

### 3. Audio-Only Mode

Strip the video stream and grab **just the audio** (music, podcasts, lectures). Output is tagged with `_audio` so it never gets mixed up with video files.

### 4. Separated Quality Lists

No more confusing mixed lists. Video and audio qualities are displayed in **two clearly labeled sections** — 📹 Video qualities and 🎧 Audio qualities — with file sizes shown for every option.

### 5. Quality Presets

Want a specific resolution? Use `360p`, `480p`, `720p`, or `1080p` as the second argument. The engine prefers MP4, automatically merges the best audio track, and falls back gracefully when a format is unavailable.

### 6. Smart URL Type Detection

Paste anything — YouTube, Facebook, Instagram, TikTok, a direct MP4 link, a PDF, an APK, or a ZIP. The tool runs a multi-stage detector (known sites → file extensions → HTTP HEAD analysis → extractor fallback) to pick the right download path.

### 7. Live Download Progress

Both the terminal and the Web UI show a **real-time progress bar** as bytes arrive — no more guessing whether your download is stuck.

### 8. Speed, ETA & Real-Time Stats

Current download speed, estimated time remaining, total size, and downloaded bytes — updated live via WebSocket pushes to the browser.

### 9. Background Downloading

Downloads run in daemon threads. Start ten downloads, keep using the app, and watch everything finish in the **Active Downloads** tab.

### 10. Concurrent Download Limits

Protect your bandwidth and device with a configurable maximum number of parallel downloads (default: 2). Enforced before any network request is made.

### 11. Download History

Every download — success or failure — is recorded with timestamp, URL, type, status, and file size. View it anytime from the terminal menu or the Web UI, and old entries are auto-cleaned from memory.

### 12. File Browser & Manager

See everything you've downloaded from a built-in file browser, open files directly, and keep track of what's taking up space.

### 13. Direct File Downloads

Non-media URLs (PDFs, ZIPs, APKs, images, documents) bypass the video extractor entirely and download through a fast, resilient direct stream — quicker and more reliable for raw files.

### 14. Resilient Resumable Sessions

Large downloads use robust HTTP sessions with automatic retry logic, so a network hiccup won't corrupt your file.

### 15. Statistics Dashboard

Total downloads, success/failure rates, and cumulative data downloaded — at a glance, in both interfaces.

### 16. Thread-Safe Architecture

All shared state (`active_downloads`, `history`) is protected with `threading.Lock`. Stress-tested with 20 concurrent threads without a single race condition.

### 17. Security Hardening

- **Path traversal protection** — malicious filenames like `../../etc/passwd` are blocked
- **No false success marks** — a failed download is always recorded as failed, never guessed as success
- **Input validation** on every API endpoint

### 18. Cross-Platform Compatibility

Written in pure Python with zero native dependencies. Runs on **Android (Termux)**, **iOS (a-Shell)**, **Windows**, **macOS**, and **Linux**. Terminal color codes degrade gracefully everywhere.

### 19. LAN Access — Share With Any Device

The web server binds to `0.0.0.0` and **auto-detects your local IP**. Your phone, tablet, or another PC on the same Wi-Fi can open the Web UI and download files too.

### 20. Persistent Settings & Config

Download directory, port, theme, and max concurrency are saved in a JSON config file — your preferences survive restarts. Override anything with CLI flags (`--port`, `--terminal-only`, `--help`).

---

## 📋 Command Cheat Sheet

| Command | Effect |
|---|---|
| `python3 duel-downloader.py` | Interactive menu (Terminal / Web / Both) |
| `python3 duel-downloader.py <URL>` | Show lists + download best quality |
| `python3 duel-downloader.py <URL> 360p` | Download in 360p |
| `python3 duel-downloader.py <URL> 480p` | Download in 480p |
| `python3 duel-downloader.py <URL> 720p` | Download in 720p |
| `python3 duel-downloader.py <URL> 1080p` | Download in 1080p |
| `python3 duel-downloader.py <URL> audio` | Audio-only download |
| `python3 duel-downloader.py <URL> mp3` | Audio-only download (alias) |
| `python3 duel-downloader.py --port 9090` | Use a custom web port |
| `python3 duel-downloader.py --terminal-only` | Skip the web server |
| `python3 duel-downloader.py --help` | Show the shortcut guide |

---

## 🖼️ Screenshots

The Web UI features a responsive design with three tabs — **Active Downloads** (live progress cards), **History** (full download log), and **Files** (browser + open actions) — all updated in real time over WebSockets.

---

## ⚙️ Requirements

| Dependency | Purpose |
|---|---|
| Python 3.8+ | Core runtime |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Video/audio extraction from 1000+ sites |
| [Flask](https://flask.palletsprojects.com/) | Web server |
| [Flask-SocketIO](https://flask-socketio.readthedocs.io/) | Real-time progress updates |
| requests | Direct file downloads |

---

## 🛣️ How It Works

```text
URL Input
   │
   ▼
┌─────────────────────────┐
│   Smart Type Detector    │  known sites → extensions → HEAD probe → extractor
└────────────┬────────────┘
             │
   ┌─────────┴──────────┐
   ▼                    ▼
Video Site?          Raw File?
   │                    │
   ▼                    ▼
┌──────────────┐  ┌──────────────┐
│  yt-dlp      │  │  Resilient   │
│  extract     │  │  stream      │
└──────┬───────┘  └──────┬───────┘
       │                 │
       ▼                 ▼
┌──────────────────────────────┐
│  DownloadEngine (threaded)   │
│  Lock-protected state        │
└──────────────┬───────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
   Terminal UI    Web UI
   (SocketIO push)
```

---

## 🧪 Testing

The project ships with automated tests covering thread safety, API behavior, path traversal protection, format list deduplication, and end-to-end real video downloads — all verified passing.

```bash
python3 test_duel.py      # unit tests
python3 test_shortcut.py  # shortcut CLI tests
```

---

## 📄 License

MIT — use it, tweak it, share it.

---

<div align="center">

**Made with ❤️ and yt-dlp**

⭐ Star this repo if you find it useful!

</div>
