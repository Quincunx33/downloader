                      
"""
🚀 iOS a-Shell Dual Mode Downloader
Mode 1: Terminal UI (for a-Shell)
Mode 2: Web GUI (for browser)
"""

import os
import sys
import json
import time
import threading
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, send_file
from flask_socketio import SocketIO
import requests
import yt_dlp
import re
from urllib.parse import urlparse, unquote

                                                           
class Config:
    def __init__(self):
                                                              
                                                                         
        self.home = Path.cwd()
        
                                                                                          
        self.web_host = "0.0.0.0"
        
                                                                           
        self.download_dir = self.home / "Downloads"
        
                                                   
        try:
            self.download_dir.mkdir(exist_ok=True)
            print(f"✓ Download directory created: {self.download_dir}")
        except Exception as e:
            print(f"⚠️ Warning: Could not create Downloads directory: {e}")
                                                                   
            self.download_dir = self.home
            print(f"✓ Using current directory: {self.download_dir}")
        
                                                   
        self.config_file = self.home / ".dualdl_config.json"
        self.history_file = self.home / ".dualdl_history.json"
        
                           
        self.web_port = 8080
        self.web_enabled = True
        
        self.load_config()
        
                                                                                                         
        if len(sys.argv) >= 3 and sys.argv[1] == '--port':
            try:
                port = int(sys.argv[2])
                if 1024 <= port <= 65535:
                    self.web_port = port
                    self.data['web_port'] = port
            except ValueError:
                print("⚠️ Invalid port argument, using 8080")
        if '--terminal-only' in sys.argv:
            self.web_enabled = False
    
    def load_config(self):
        defaults = {
            "theme": "dark",
            "default_format": "best",
            "max_concurrent": 2,
            "web_port": 8080,
            "web_host": "0.0.0.0",
            "auto_open_browser": True,
            "video_sites": [
                "youtube.com", "youtu.be", "facebook.com", "fb.watch",
                "instagram.com", "tiktok.com", "twitter.com", "x.com",
                "vimeo.com", "dailymotion.com", "twitch.tv"
            ],
            "download_dir": str(self.download_dir)
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_data = json.load(f)
                                                     
                    self.data = {**defaults, **loaded_data}
                                                                     
                    if 'download_dir' in loaded_data:
                        try:
                            self.download_dir = Path(loaded_data['download_dir'])
                            self.download_dir.mkdir(exist_ok=True)
                        except:
                            pass                                    
            except Exception as e:
                print(f"⚠️ Config load error: {e}")
                self.data = defaults
        else:
            self.data = defaults
        
        self.web_port = self.data.get('web_port', 8080)
        self.web_host = self.data.get('web_host', '0.0.0.0')
    
    def save(self):
                                                     
        self.data['download_dir'] = str(self.download_dir)
        self.data['web_port'] = self.web_port
        self.data['web_host'] = self.web_host
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            return True
        except Exception as e:
            print(f"❌ Error saving config: {e}")
            return False

                                                           
class DownloadEngine:
    def __init__(self, config):
        self.config = config
        self.active_downloads = {}
        self.history = self.load_history()
        self.socketio = None
        
                            
        self.user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
        
                                                                    
        self._lock = threading.Lock()
        
                                                        
        self._cleanup_timer = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self._cleanup_timer.start()
    
    def _periodic_cleanup(self):
        """completed/failed entries 15 মিনিট পর memory থেকে remove"""
        while True:
            time.sleep(600)
            try:
                with self._lock:
                    cutoff = time.time() - 900
                    self.active_downloads = {
                        k: v for k, v in self.active_downloads.items()
                        if v.get('started_at', 0) > cutoff
                    }
            except Exception:
                pass
    
    def load_history(self):
        if self.config.history_file.exists():
            try:
                with open(self.config.history_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_history(self):
        try:
            with open(self.config.history_file, 'w') as f:
                json.dump(self.history[-100:], f, indent=2)
        except Exception as e:
            print(f"⚠️ History save error: {e}")
    
    def add_history(self, url, filename, success=True, size=0, download_type=""):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "url": url[:100],
            "filename": filename,
            "success": success,
            "size": size,
            "type": download_type,
            "status": "completed" if success else "failed"
        }
        with self._lock:
            entry["id"] = len(self.history) + 1
            self.history.append(entry)
        self.save_history()
        
                                       
        if self.socketio:
            self.socketio.emit('history_update', entry)
    
    def detect_type(self, url):
        """Detect if URL is video, image, or file"""
        url_lower = url.lower()
        
                           
        for site in self.config.data['video_sites']:
            if site in url_lower:
                return 'video'
        
                               
        file_exts = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.mp3', 
                    '.mp4', '.avi', '.mkv', '.zip', '.rar', '.7z',
                    '.apk', '.exe', '.dmg', '.deb', '.txt', '.doc', 
                    '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        
        for ext in file_exts:
            if url_lower.endswith(ext):
                return 'file'
        
                                                                   
        known_video_like_domains = [
            'mediafire.com', 'dropbox.com', 'drive.google.com', 'wetransfer.com',
            'mega.nz', 'archive.org', 'reddit.com', 'imgur.com', 'flickr.com'
        ]
        for domain in known_video_like_domains:
            if domain in url_lower:
                return 'file'                                                             
        
                                                                                                          
        try:
            resp = requests.head(url, timeout=5, 
                               headers={'User-Agent': self.user_agent},
                               allow_redirects=True)
            content_type = resp.headers.get('content-type', '').lower()
            
            if 'video' in content_type:
                return 'video'
            elif 'image' in content_type:
                return 'image'
            elif 'audio' in content_type:
                return 'audio'
            elif 'pdf' in content_type:
                return 'pdf'
            elif 'zip' in content_type or 'rar' in content_type or '7z' in content_type:
                return 'archive'
            elif 'text' in content_type:
                return 'text'
        except Exception:
            pass
        
                                                                          
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'extract_flat': True}) as ydl:
                ydl.extract_info(url, download=False)
            return 'video'
        except Exception:
            pass
        
        return 'unknown'
    
    def get_video_info(self, url):
        """Get video information"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                result = {
                    'title': info.get('title', 'Unknown'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'formats': []
                }
                
                                
                for fmt in info.get('formats', []):
                    if fmt.get('vcodec') != 'none':
                        result['formats'].append({
                            'format_id': fmt.get('format_id'),
                            'ext': fmt.get('ext', 'mp4'),
                            'resolution': fmt.get('resolution', 'unknown'),
                            'format_note': fmt.get('format_note', 'unknown'),
                            'filesize': fmt.get('filesize', 0),
                            'height': fmt.get('height', 0),
                            'acodec': fmt.get('acodec', 'none')
                        })
                
                                                                           
                result['formats'] = [f for f in result['formats'] if f['resolution'] != 'unknown']
                result['formats'].sort(key=lambda f: f['height'], reverse=True)
                
                return result
        except Exception as e:
            return {'error': str(e)}
    
    def get_format_lists(self, url):
        """ভিডিও ও অডিও আলাদা, dedupe করা format list return করে — shortcut system এর জন্ে"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                uploader = info.get('uploader', 'Unknown')
                
                video_formats, audio_formats = [], []
                seen_video = set()                                 
                seen_audio = set()                          
                
                for fmt in info.get('formats', []):
                    if fmt.get('vcodec') != 'none':
                        res = fmt.get('resolution', 'unknown')
                        if res == 'unknown' or not fmt.get('height'):
                            continue
                        key = (res, fmt.get('ext', 'mp4'))
                        if key in seen_video:
                            continue
                        seen_video.add(key)
                        video_formats.append({
                            'format_id': fmt.get('format_id'),
                            'resolution': res,
                            'ext': fmt.get('ext', 'mp4'),
                            'fps': fmt.get('fps', 0) or 0,
                            'filesize': fmt.get('filesize', 0) or 0,
                            'height': fmt.get('height', 0),
                        })
                    elif fmt.get('acodec') != 'none':
                        abr = fmt.get('abr') or 0
                        key = (round(abr), fmt.get('ext', 'm4a'))
                        if key in seen_audio or not abr:
                            continue
                        seen_audio.add(key)
                        audio_formats.append({
                            'format_id': fmt.get('format_id'),
                            'abr': abr,
                            'ext': fmt.get('ext', 'm4a'),
                            'filesize': fmt.get('filesize', 0) or 0,
                        })
                
                                                                              
                video_formats.sort(key=lambda f: f['height'], reverse=True)
                audio_formats.sort(key=lambda f: f['abr'], reverse=True)
                
                return {
                    'title': title,
                    'uploader': uploader,
                    'duration': duration,
                    'videos': video_formats,
                    'audios': audio_formats,
                }
        except Exception as e:
            return {'error': str(e)}
    
    def download_video(self, url, format_id='best', download_id=None):
        """Download video with progress tracking"""
        download_id = download_id or f"vid_{int(time.time())}"
        
        def download_thread():
            try:
                                                 
                with self._lock:
                    active_count = sum(
                        1 for v in self.active_downloads.values()
                        if v.get('status') == 'downloading'
                    )
                if active_count >= self.config.data.get('max_concurrent', 2):
                    raise Exception(
                        f"Concurrent download limit reached "
                        f"({self.config.data.get('max_concurrent', 2)}). "
                        "Wait for an active download to finish."
                    )
                
                               
                with self._lock:
                    self.active_downloads[download_id] = {
                        'status': 'downloading',
                        'progress': 0,
                        'filename': None,
                        'speed': '0 KB/s',
                        'eta': '--:--',
                        'started_at': time.time()
                    }
                    status_snapshot = dict(self.active_downloads[download_id])
                
                if self.socketio:
                    self.socketio.emit('download_update', status_snapshot)
                
                                  
                format_query_map = {
                    'mp4': 'bv*[ext=mp4][height<=?1080]+ba/b[ext=mp4]/bv*+ba/b',
                    'webm': 'bv*[ext=webm]+ba/b[ext=webm]/bv*+ba/b',
                    'worst': 'worst',
                                                                         
                    '720p': 'bv*[height<=720][ext=mp4]+ba/b[ext=mp4]/bv*[height<=720]+ba/b[height<=720]/best[height<=720]',
                    '1080p': 'bv*[height<=1080][ext=mp4]+ba/b[ext=mp4]/bv*[height<=1080]+ba/b[height<=1080]/best[height<=1080]',
                    '480p': 'bv*[height<=480][ext=mp4]+ba/b[ext=mp4]/bv*[height<=480]+ba/b[height<=480]/best[height<=480]',
                    '360p': 'bv*[height<=360][ext=mp4]+ba/b[ext=mp4]/bv*[height<=360]+ba/b[height<=360]/best[height<=360]',
                    'worst[height<=?480]': 'worst[height<=?480]',
                }
                if format_id in format_query_map:
                    dl_format = format_query_map[format_id]
                elif format_id == 'best':
                    dl_format = 'best'
                else:
                                                                                  
                    dl_format = f"{format_id}+bestaudio/best"
                
                                                                                        
                if format_id == 'audio':
                    dl_format = 'bestaudio/best'
                    filename_template = f"%(title)s_{download_id}_audio.%(ext)s"
                else:
                    filename_template = f"%(title)s_{download_id}.%(ext)s"
                ydl_opts = {
                    'format': dl_format,
                    'outtmpl': str(self.config.download_dir / filename_template),
                    'progress_hooks': [self.progress_hook_factory(download_id)],
                    'quiet': False,
                    'no_warnings': True,
                    'socket_timeout': 30,
                    'retries': 3,
                }
                
                                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                                      
                downloaded_files = list(self.config.download_dir.glob(f"*{download_id}*"))
                if downloaded_files:
                    filename = downloaded_files[0].name
                    filesize = downloaded_files[0].stat().st_size
                    
                                   
                    with self._lock:
                        self.active_downloads[download_id].update({
                            'status': 'completed',
                            'progress': 100,
                            'filename': filename,
                            'filesize': filesize
                        })
                    
                    self.add_history(
                        url, filename, True,
                        filesize, "video"
                    )
                else:
                                                                    
                                                                                         
                    raise Exception("Downloaded file not found in output directory")
                
            except Exception as e:
                print(f"❌ Video download error: {e}")
                with self._lock:
                    self.active_downloads[download_id] = {
                        'status': 'failed',
                        'error': str(e)
                    }
                self.add_history(url, "", False, 0, "video")
            
                          
            if self.socketio:
                with self._lock:
                    status_snapshot = dict(self.active_downloads[download_id])
                self.socketio.emit('download_update', status_snapshot)
        
                         
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()
        
        return download_id
    
    def progress_hook_factory(self, download_id):
        """Create progress hook for specific download"""
        def progress_hook(d):
            if d['status'] == 'downloading':
                percent = d.get('_percent_str', '0%').strip('%')
                try:
                    progress = float(percent)
                    with self._lock:
                        self.active_downloads[download_id].update({
                            'progress': progress,
                            'speed': d.get('_speed_str', '0 KB/s'),
                            'eta': d.get('_eta_str', '--:--'),
                            'total_bytes': d.get('total_bytes', 0),
                            'downloaded_bytes': d.get('downloaded_bytes', 0)
                        })
                    
                    if self.socketio:
                        self.socketio.emit('download_progress', {
                            'id': download_id,
                            'progress': progress,
                            'speed': d.get('_speed_str', '0 KB/s'),
                            'eta': d.get('_eta_str', '--:--')
                        })
                except Exception:
                    pass
        return progress_hook
    
    def download_file(self, url, download_id=None):
        """Download general files"""
        download_id = download_id or f"file_{int(time.time())}"
        
        def download_thread():
            try:
                                                                                  
                with self._lock:
                    active_count = sum(
                        1 for v in self.active_downloads.values()
                        if v.get('status') == 'downloading'
                    )
                if active_count >= self.config.data.get('max_concurrent', 2):
                    raise Exception(
                        f"Concurrent download limit reached "
                        f"({self.config.data.get('max_concurrent', 2)}). "
                        "Wait for an active download to finish."
                    )
                
                headers = {'User-Agent': self.user_agent}
                session = requests.Session()
                adapter = requests.adapters.HTTPAdapter(max_retries=3)
                session.mount('http://', adapter)
                session.mount('https://', adapter)
                response = session.get(url, stream=True, headers=headers, timeout=30)
                response.raise_for_status()
                
                                                                              
                filename = None
                if 'content-disposition' in response.headers:
                    cd = response.headers['content-disposition']
                    if 'filename=' in cd:
                        filename = cd.split('filename=')[1].split(';')[0].strip('"').strip("'")
                                                       
                if not filename and 'filename*' in response.headers.get('content-disposition', ''):
                    cd = response.headers['content-disposition']
                    match = re.search(r"filename\*=UTF-8''(.+?)(?:;|$)", cd)
                    if match:
                        filename = unquote(match.group(1))
                
                if not filename:
                    parsed = urlparse(url)
                    filename = os.path.basename(parsed.path)
                    filename = unquote(filename)
                
                                
                filename = re.sub(r'[^\w\-_\. ]', '', filename)
                if not filename or len(filename) < 3:
                    filename = f"download_{download_id}.bin"
                
                           
                filepath = self.config.download_dir / filename
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                self.active_downloads[download_id] = {
                    'status': 'downloading',
                    'progress': 0,
                    'filename': filename,
                    'total_size': total_size,
                    'started_at': time.time()
                }
                
                if self.socketio:
                    self.socketio.emit('download_update', self.active_downloads[download_id])
                
                                        
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                with self._lock:
                                    self.active_downloads[download_id]['progress'] = progress
                                
                                if self.socketio:
                                    self.socketio.emit('download_progress', {
                                        'id': download_id,
                                        'progress': progress,
                                        'downloaded': downloaded,
                                        'total': total_size
                                    })
                
                          
                with self._lock:
                    self.active_downloads[download_id].update({
                        'status': 'completed',
                        'progress': 100,
                        'filesize': os.path.getsize(filepath)
                    })
                
                self.add_history(
                    url, filename, True,
                    os.path.getsize(filepath), "file"
                )
                
            except Exception as e:
                print(f"❌ File download error: {e}")
                with self._lock:
                    self.active_downloads[download_id] = {
                        'status': 'failed',
                        'error': str(e)
                    }
                self.add_history(url, "", False, 0, "file")
            
                          
            if self.socketio:
                with self._lock:
                    status_snapshot = dict(self.active_downloads[download_id])
                self.socketio.emit('download_update', status_snapshot)
        
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()
        
        return download_id

                                                           
class WebInterface:
    def __init__(self, engine, config):
        self.engine = engine
        self.config = config
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.engine.socketio = self.socketio
        
        self.setup_routes()
        self.setup_events()
    
    def setup_routes(self):
        @self.app.route('/')
        def index():
            return self.render_main()
        
        @self.app.route('/api/analyze', methods=['POST'])
        def api_analyze():
            url = request.json.get('url', '')
            if not url:
                return jsonify({'error': 'URL required'}), 400
            
            url_type = self.engine.detect_type(url)
            result = {'type': url_type}
            
            if url_type == 'video':
                video_info = self.engine.get_video_info(url)
                result.update(video_info)
            
            return jsonify(result)
        
        @self.app.route('/api/active')
        def api_active():
            """Active downloads ট্যাব এর জন্য — শুধু in-progress entries return করে"""
            with self.engine._lock:
                active = [
                    dict(v) for v in self.engine.active_downloads.values()
                    if v.get('status') == 'downloading'
                ]
            return jsonify(active)
        
        @self.app.route('/api/download', methods=['POST'])
        def api_download():
            data = request.json
            url = data.get('url', '')
            format_id = data.get('format', 'best')
            
            if not url:
                return jsonify({'error': 'URL required'}), 400
            
            url_type = self.engine.detect_type(url)
            
            if url_type == 'video':
                download_id = self.engine.download_video(url, format_id)
            else:
                download_id = self.engine.download_file(url)
            
            return jsonify({
                'download_id': download_id,
                'type': url_type,
                'message': 'Download started'
            })
        
        @self.app.route('/api/status/<download_id>')
        def api_status(download_id):
            with self.engine._lock:
                status = dict(self.engine.active_downloads.get(download_id, {'error': 'Not found'}))
            return jsonify(status)
        
        @self.app.route('/api/history')
        def api_history():
            return jsonify(self.engine.history[-20:])           
        
        @self.app.route('/api/files')
        def api_files():
            files = []
            try:
                for f in self.config.download_dir.glob('*'):
                    if f.is_file() and not f.name.startswith('.'):
                        files.append({
                            'name': f.name,
                            'size': f.stat().st_size,
                            'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                        })
            except Exception as e:
                print(f"⚠️ Error listing files: {e}")
            
            return jsonify(sorted(files, key=lambda x: x['modified'], reverse=True)[:20])
        
        @self.app.route('/api/open/<filename>')
        def api_open(filename):
                                                                    
            if '..' in filename or '/' in filename or '\\' in filename:
                return jsonify({'error': 'Invalid filename'}), 400
            filepath = (self.config.download_dir / filename).resolve()
                                                                          
            if not str(filepath).startswith(str(self.config.download_dir.resolve())):
                return jsonify({'error': 'Invalid filename'}), 400
            if filepath.exists():
                                                                               
                if filename.endswith(('.txt', '.json', '.py', '.html', '.css', '.js')):
                    with open(filepath, 'r') as f:
                        return f.read()[:5000]
                return send_file(filepath)
            return jsonify({'error': 'File not found'}), 404
    
    def setup_events(self):
        @self.socketio.on('connect')
        def handle_connect():
            print(f"Client connected: {request.sid}")
    
    def render_main(self):
        """HTML template for web interface"""
        return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 iOS Downloader - Web UI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .subtitle {
            opacity: 0.9;
            font-weight: 300;
        }
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            padding: 30px;
        }
        @media (max-width: 768px) {
            .main-content { grid-template-columns: 1fr; }
        }
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .card h2 {
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }
        .form-group {
            margin-bottom: 20px;
        }
        input, select, button {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        button:active {
            transform: translateY(0);
        }
        .progress-container {
            margin-top: 20px;
        }
        .progress-bar {
            height: 20px;
            background: #f0f0f0;
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 10px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 10px;
            width: 0%;
            transition: width 0.3s;
        }
        .download-item {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .status {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .status.downloading { background: #fff3cd; color: #856404; }
        .status.completed { background: #d4edda; color: #155724; }
        .status.failed { background: #f8d7da; color: #721c24; }
        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        .file-item:hover {
            background: #f8f9fa;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 20px;
        }
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: 700;
        }
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        .tab-container {
            margin-top: 20px;
        }
        .tabs {
            display: flex;
            border-bottom: 2px solid #f0f0f0;
            margin-bottom: 20px;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            font-weight: 500;
            border-bottom: 3px solid transparent;
        }
        .tab.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .info-box {
            background: #e7f3ff;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 15px 0;
            border-radius: 0 10px 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 iOS Advanced Downloader</h1>
            <p class="subtitle">Dual Mode: Terminal + Web Interface | Running on a-Shell</p>
        </header>
        
        <div class="main-content">
            <!-- Left Column -->
            <div class="card">
                <h2>📥 Download Manager</h2>
                
                <div class="form-group">
                    <input type="url" id="urlInput" 
                           placeholder="https://youtube.com/watch?v=... or any file URL" 
                           required>
                </div>
                
                <div class="form-group" id="formatGroup" style="display:none;">
                    <select id="formatSelect">
                        <option value="best">Best Quality (Auto)</option>
                        <option value="worst">Worst Quality (Smallest)</option>
                        <option value="mp4">MP4 Format</option>
                        <option value="webm">WebM Format</option>
                    </select>
                </div>
                
                <button onclick="analyzeUrl()">🔍 Analyze URL</button>
                <button onclick="startDownload()" id="downloadBtn" style="display:none; margin-top:10px;">
                    ⬇️ Start Download
                </button>
                
                <div id="videoInfo" style="display:none; margin-top:20px;">
                    <div class="info-box" id="infoContent"></div>
                </div>
                
                <div class="progress-container" id="progressContainer" style="display:none;">
                    <h3>Download Progress</h3>
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill"></div>
                    </div>
                    <div id="progressText">0% | Speed: 0 KB/s | ETA: --:--</div>
                </div>
            </div>
            
            <!-- Right Column -->
            <div class="card">
                <div class="tab-container">
                    <div class="tabs">
                        <div class="tab active" onclick="showTab('downloads')">📥 Active</div>
                        <div class="tab" onclick="showTab('history')">📋 History</div>
                        <div class="tab" onclick="showTab('files')">📁 Files</div>
                        <div class="tab" onclick="showTab('stats')">📊 Stats</div>
                    </div>
                    
                    <div id="downloadsTab" class="tab-content active">
                        <h3>Active Downloads</h3>
                        <div id="activeDownloads"></div>
                    </div>
                    
                    <div id="historyTab" class="tab-content">
                        <h3>Download History</h3>
                        <div id="downloadHistory"></div>
                    </div>
                    
                    <div id="filesTab" class="tab-content">
                        <h3>Downloaded Files</h3>
                        <div id="fileList"></div>
                    </div>
                    
                    <div id="statsTab" class="tab-content">
                        <h3>Statistics</h3>
                        <div class="stats">
                            <div class="stat-box">
                                <div class="stat-value" id="totalDownloads">0</div>
                                <div class="stat-label">Total</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-value" id="successfulDownloads">0</div>
                                <div class="stat-label">Successful</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-value" id="totalSize">0 MB</div>
                                <div class="stat-label">Total Size</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div style="padding: 20px; text-align: center; color: #666; font-size: 14px;">
            <p>🌐 Server running on: <span id="serverUrl">localhost:{{ port }}</span> | 
               📱 Open on other devices: <input type="text" id="shareUrl" style="width:300px; padding:5px; font-size:12px;" readonly>
               <button onclick="copyShareUrl()" style="padding:5px 10px; font-size:12px;">Copy</button>
            </p>
        </div>
    </div>
    
    <script>
        const socket = io();
        let currentDownloadId = null;
        const serverPort = {{ port }};
        const serverIp = window.location.hostname;
        
        // Update share URL
        document.getElementById('shareUrl').value = `http://${serverIp}:${serverPort}`;
        document.getElementById('serverUrl').textContent = `http://${serverIp}:${serverPort}`;
        
        function copyShareUrl() {
            const url = document.getElementById('shareUrl');
            url.select();
            document.execCommand('copy');
            alert('URL copied! Open this on other devices.');
        }
        
        // Socket events
        socket.on('download_update', function(data) {
            updateDownloadStatus(data);
        });
        
        socket.on('download_progress', function(data) {
            updateProgress(data);
        });
        
        socket.on('history_update', function(data) {
            loadHistory();
            loadStats();
        });
        
        // Tab management
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            event.target.classList.add('active');
            document.getElementById(tabName + 'Tab').classList.add('active');
        }
        
        // URL analysis
        async function analyzeUrl() {
            const url = document.getElementById('urlInput').value.trim();
            if (!url) return alert('Please enter a URL');
            
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url: url})
            });
            
            const data = await response.json();
            
            if (data.type === 'video') {
                document.getElementById('formatGroup').style.display = 'block';
                document.getElementById('downloadBtn').style.display = 'block';
                document.getElementById('videoInfo').style.display = 'block';
                
                let infoHtml = `<strong>🎬 ${data.title || 'Video'}</strong><br>`;
                if (data.uploader) infoHtml += `👤 ${data.uploader}<br>`;
                if (data.duration) {
                    const mins = Math.floor(data.duration / 60);
                    const secs = data.duration % 60;
                    infoHtml += `⏱️ ${mins}:${secs.toString().padStart(2, '0')}<br>`;
                }
                
                let options = '<option value="best">Best Quality (Auto)</option>';
                data.formats.forEach((fmt, index) => {
                    const size_mb = fmt.filesize ? (fmt.filesize / (1024*1024)).toFixed(1) + 'MB' : 'Unknown';
                    options += `<option value="${fmt.format_id}">${fmt.resolution} (${fmt.format_note}) - ${size_mb}</option>`;
                });
                document.getElementById('formatSelect').innerHTML = options;
                
                document.getElementById('infoContent').innerHTML = infoHtml;
            } else {
                document.getElementById('formatGroup').style.display = 'none';
                document.getElementById('downloadBtn').style.display = 'block';
                document.getElementById('videoInfo').style.display = 'none';
            }
        }
        
        // Start download
        async function startDownload() {
            const url = document.getElementById('urlInput').value.trim();
            const format = document.getElementById('formatSelect').value;
            
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url: url, format: format})
            });
            
            const data = await response.json();
            
            if (data.download_id) {
                currentDownloadId = data.download_id;
                document.getElementById('progressContainer').style.display = 'block';
                loadActiveDownloads();
            } else {
                alert('Failed to start download');
            }
        }
        
        // Update progress
        function updateProgress(data) {
            if (data.id === currentDownloadId) {
                document.getElementById('progressFill').style.width = data.progress + '%';
                document.getElementById('progressText').textContent = 
                    `${data.progress.toFixed(1)}% | Speed: ${data.speed || '0 KB/s'} | ETA: ${data.eta || '--:--'}`;
            }
        }
        
        // Update download status
        function updateDownloadStatus(data) {
            loadActiveDownloads();
            if (data.status === 'completed') {
                setTimeout(() => {
                    loadHistory();
                    loadFiles();
                    loadStats();
                }, 1000);
            }
        }
        
        // Load active downloads (live status from /api/active — memory তে থাকা in-progress entries)
        async function loadActiveDownloads() {
            const response = await fetch('/api/active');
            const active = await response.json();
            
            let html = '';
            active.forEach(item => {
                const progress = item.progress != null ? `${item.progress.toFixed(1)}%` : '0%';
                const speed = item.speed || '';
                const eta = item.eta || '--:--';
                const sizeInfo = item.total_bytes
                    ? ` | ${(item.downloaded_bytes || 0) / 1048576}MB / ${(item.total_bytes / 1048576).toFixed(1)}MB`
                    : '';
                html += `
                    <div class="download-item">
                        <div>
                            <strong>${item.filename || 'Downloading...'}</strong><br>
                            <small>${progress} | ${speed} | ETA: ${eta}${sizeInfo}</small>
                        </div>
                        <div class="status ${item.status}">
                            ${item.status}
                        </div>
                    </div>
                `;
            });
            
            if (html === '') {
                html = '<p style="text-align:center;color:#999;">No active downloads</p>';
            }
            
            document.getElementById('activeDownloads').innerHTML = html;
        }
        
        // Load history
        async function loadHistory() {
            const response = await fetch('/api/history');
            const history = await response.json();
            
            let html = '';
            history.reverse().forEach(item => {
                const date = new Date(item.timestamp).toLocaleString();
                html += `
                    <div class="download-item">
                        <div>
                            <strong>${item.filename || 'Unknown'}</strong><br>
                            <small>${date} | ${item.url}</small>
                        </div>
                        <div class="status ${item.success ? 'completed' : 'failed'}">
                            ${item.success ? '✓' : '✗'}
                        </div>
                    </div>
                `;
            });
            
            document.getElementById('downloadHistory').innerHTML = html;
        }
        
        // Load files
        async function loadFiles() {
            const response = await fetch('/api/files');
            const files = await response.json();
            
            let html = '';
            files.forEach(file => {
                const sizeMB = (file.size / (1024*1024)).toFixed(2);
                const date = new Date(file.modified).toLocaleDateString();
                html += `
                    <div class="file-item">
                        <div>${file.name}</div>
                        <div style="color:#666; font-size:0.9em;">
                            ${sizeMB} MB | ${date}
                        </div>
                    </div>
                `;
            });
            
            document.getElementById('fileList').innerHTML = html;
        }
        
        // Load statistics
        async function loadStats() {
            const response = await fetch('/api/history');
            const history = await response.json();
            
            const total = history.length;
            const successful = history.filter(h => h.success).length;
            const totalSize = history.reduce((sum, h) => sum + (h.size || 0), 0) / (1024*1024);
            
            document.getElementById('totalDownloads').textContent = total;
            document.getElementById('successfulDownloads').textContent = successful;
            document.getElementById('totalSize').textContent = totalSize.toFixed(1) + ' MB';
        }
        
        // Initial load
        window.onload = function() {
            loadActiveDownloads();
            loadHistory();
            loadFiles();
            loadStats();
            
            // Auto-refresh every 2 seconds (live progress এর জন্য)
            setInterval(loadActiveDownloads, 2000);
        };
    </script>
</body>
</html>
        ''', port=self.config.web_port)
    
    def start(self):
        """Start the web server"""
        print(f"\n🌐 Starting Web Server on: http://{self.config.web_host}:{self.config.web_port}")
                                                                   
        try:
            import socket as _s
            _sock = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
            _sock.connect(("8.8.8.8", 80))
            lan_ip = _sock.getsockname()[0]
            _sock.close()
            print(f"📱 Open on other devices: http://{lan_ip}:{self.config.web_port}")
        except Exception:
            print(f"📱 Open on other devices: http://YOUR_IP:{self.config.web_port}")
        print("🔄 Press Ctrl+C to stop web server\n")
        
                             
        if self.config.data.get('auto_open_browser', True):
            try:
                webbrowser.open(f"http://{self.config.web_host}:{self.config.web_port}")
            except:
                pass
        
        try:
            self.socketio.run(
                self.app, 
                host=self.config.web_host, 
                port=self.config.web_port,
                debug=False, 
                use_reloader=False,
                allow_unsafe_werkzeug=True
            )
        except Exception as e:
            print(f"❌ Web server error: {e}")
            print("⚠️ Try using a different port: python3 duel-downloader.py --port 8081")

                                                           
class TerminalInterface:
    def __init__(self, engine, config):
        self.engine = engine
        self.config = config
    
    @staticmethod
    def _human_size(n):
        if not n:
            return '?'
        mb = n / 1048576
        return f"{mb:.1f}MB" if mb >= 1 else f"{(n/1024):.0f}KB"
    
    @staticmethod
    def _size(n):
        """ছোট হেল্পার — shortcut finish message-এ size ফরম্যাট"""
        if not n:
            return '0 MB'
        mb = n / 1048576
        return f"{mb:.2f} MB" if mb >= 1 else f"{n/1024:.0f} KB"
    
    def print_format_lists(self, info):
        """ভিডিও ও অডিও আলাদা করে, dedupe করে list দেখায় — shortcut mode"""
        title = info.get('title', 'Unknown')
        duration = info.get('duration', 0)
        if duration:
            mins = duration // 60
            secs = duration % 60
            dur_str = f" | ⏱ {mins}:{secs:02d}"
        else:
            dur_str = ''
        print(f"\n\033[32m🎬 {title}{dur_str}\033[0m")
        
        videos = info.get('videos', [])
        audios = info.get('audios', [])
        
                     
        if videos:
            print(f"\n\033[36m📹 Video qualities (number টা type করবেন quality বেছে নিতে):\033[0m")
            print("\033[90m" + "-" * 58 + "\033[0m")
            for i, f in enumerate(videos, 1):
                print(f"  \033[33m{i:>2d}\033[0m. {f['resolution']:<8s} {f['ext']:<4s} | {self._human_size(f['filesize']):>6s}")
            print("\033[90m" + "-" * 58 + "\033[0m")
        else:
            print("\n\033[90m📹 কোনো ভিডিও format পাওয়া যায়নি\033[0m")
        
                    
        if audios:
            print(f"\n\033[36m🎧 Audio qualities:\033[0m")
            print("\033[90m" + "-" * 58 + "\033[0m")
            for i, f in enumerate(audios, 1):
                print(f"  \033[33m{i:>2d}\033[0m. {f['abr']:<6.0f}kbps {f['ext']:<4s} | {self._human_size(f['filesize']):>6s}")
            print("\033[90m" + "-" * 58 + "\033[0m")
        else:
            print("\n\033[90m🎧 অডিও আলাদা করে বের করা যাচ্ছে না (best audio merge হবে)\033[0m")
    
    def quick_download(self, url, mode='best'):
        """Shortcut system: এক command-এ ভিডিও/অডিও/কোয়ালিটি ডাউনলোড"""
        print(f"\n\033[36m⚡ Quick download: {url}\033[0m")
        
        url_type = self.engine.detect_type(url)
        if url_type != 'video':
                                                    
            did = self.engine.download_file(url)
            print(f"\033[32m✅ Download started (file)! ID: {did}\033[0m")
            return
        
        print("\033[36m📊 Format লিস্ট বের করছি...\033[0m")
        info = self.engine.get_format_lists(url)
        if 'error' in info:
            print(f"\033[31m❌ Error: {info['error']}\033[0m")
            return
        
        self.print_format_lists(info)
        
        if mode == 'audio':
                                                   
            print("\n\033[36m🎧 Audio download mode — best audio (video ছাড়া) download হচ্ছে\033[0m")
            did = self.engine.download_video(url, 'audio')
        else:
            did = self.engine.download_video(url, mode)
            if mode != 'best':
                print(f"\n\033[36m🎬 Quality preset: {mode}\033[0m")
            else:
                print(f"\n\033[36m🎬 Best quality-তে download হচ্ছে\033[0m")
        print(f"\033[32m✅ Download started! ID: {did}\033[0m")
        print(f"\033[90mDownloading to: {self.config.download_dir}\033[0m")
        print("\033[90mCheck Web UI for progress or wait...\033[0m")
    
    def print_header(self):
                                                                                
        try:
            print('\033c', end='')
        except Exception:
            os.system('clear' if os.name == 'posix' else 'cls')
        print("\033[36m" + "═" * 60)
        print("   🚀 iOS DUAL MODE DOWNLOADER")
        print("   Terminal + Web Interface")
        print("═" * 60 + "\033[0m")
        print(f"📁 Download dir: {self.config.download_dir}")
        print(f"🌐 Web UI: http://localhost:{self.config.web_port}")
        print()
    
    def main_menu(self):
        while True:
            self.print_header()
            print("\033[33m1\033[0m. 📥 Download URL")
            print("\033[33m2\033[0m. 🌐 Start Web Server")
            print("\033[33m3\033[0m. 📋 View History")
            print("\033[33m4\033[0m. 📁 View Files")
            print("\033[33m5\033[0m. ⚙️ Settings")
            print("\033[33m6\033[0m. 📊 Statistics")
            print("\033[33m0\033[0m. 🚪 Exit")
            print()
            
            choice = input("\033[36m👉 Select option: \033[0m").strip()
            
            if choice == '1':
                self.download_url()
            elif choice == '2':
                self.start_web_server()
            elif choice == '3':
                self.view_history()
            elif choice == '4':
                self.view_files()
            elif choice == '5':
                self.settings()
            elif choice == '6':
                self.statistics()
            elif choice == '0':
                print("\n\033[32mGoodbye! 👋\033[0m")
                break
    
    def download_url(self):
        self.print_header()
        print("\033[36m📥 Download URL\033[0m")
        print("\033[90mEnter URL or 'back' to return\033[0m")
        print()
        
        url = input("\033[33mURL: \033[0m").strip()
        if url.lower() in ['back', 'b', '']:
            return
        
        print("\n\033[36m🔍 Detecting URL type...\033[0m")
        url_type = self.engine.detect_type(url)
        print(f"\033[36mDetected type: {url_type}\033[0m")
        
        if url_type == 'video':
            print("\033[36m📊 Getting video info...\033[0m")
            info = self.engine.get_video_info(url)
            if 'error' not in info:
                print(f"\n\033[32m🎬 Title: {info['title']}\033[0m")
                print(f"\033[90m👤 Uploader: {info['uploader']}\033[0m")
                
                if info['formats']:
                    print("\n\033[33mAvailable formats:\033[0m")
                    for i, fmt in enumerate(info['formats'], 1):
                        size_mb = fmt['filesize'] / (1024*1024) if fmt['filesize'] else 0
                        print(f"  {i}. {fmt['resolution']} ({fmt['format_note']}) - {size_mb:.1f}MB")
                    
                    print("\n\033[33mSelect format number (or Enter for best): \033[0m", end='')
                    choice = input().strip()
                    
                    format_id = 'best'
                    if choice.isdigit() and 1 <= int(choice) <= len(info['formats']):
                        format_id = info['formats'][int(choice)-1]['format_id']
            
            download_id = self.engine.download_video(url, format_id)
            print(f"\n\033[32m✅ Download started! ID: {download_id}\033[0m")
            print(f"\033[90mDownloading to: {self.config.download_dir}\033[0m")
            print("\033[90mCheck Web UI for progress or wait...\033[0m")
            
        else:
            download_id = self.engine.download_file(url)
            print(f"\n\033[32m✅ Download started! ID: {download_id}\033[0m")
            print(f"\033[90mDownloading to: {self.config.download_dir}\033[0m")
        
        print("\n\033[33m📥 Downloads will continue in background.\033[0m")
        input("\n\033[90mPress Enter to continue...\033[0m")
    
    def start_web_server(self):
        self.print_header()
        print("\033[36m🌐 Starting Web Server\033[0m")
        print("\033[90mWeb interface will open in browser\033[0m")
        print()
        
                                               
        web_interface = WebInterface(self.engine, self.config)
        
        def run_server():
            try:
                web_interface.start()
            except Exception as e:
                print(f"\033[31m❌ Web server error: {e}\033[0m")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        print("\033[32m✅ Web server started!\033[0m")
        print(f"\033[36m📡 Open: http://localhost:{self.config.web_port}\033[0m")
        print(f"\033[90m📱 On other devices: http://YOUR_IP:{self.config.web_port}\033[0m")
        print("\n\033[33m⚠️  Server running in background. Press Enter to return to menu.\033[0m")
        input()
    
    def view_history(self):
        self.print_header()
        print("\033[36m📋 Download History\033[0m")
        print()
        
        if not self.engine.history:
            print("\033[90mNo history found\033[0m")
        else:
            print("\033[90mID  | Date       | Type   | Status   | Size     | URL\033[0m")
            print("\033[90m" + "-" * 80 + "\033[0m")
            
            for item in reversed(self.engine.history[-20:]):
                date = item['timestamp'].split('T')[0]
                status = "✅" if item['success'] else "❌"
                size_mb = item['size'] / (1024*1024) if item['size'] else 0
                url_short = item['url'][:40] + "..." if len(item['url']) > 40 else item['url']
                
                print(f"{item['id']:3d} | {date} | {item['type']:6s} | {status:^8s} | {size_mb:6.1f}MB | {url_short}")
        
        print()
        input("\033[90mPress Enter to continue...\033[0m")
    
    def view_files(self):
        self.print_header()
        print("\033[36m📁 Downloaded Files\033[0m")
        print()
        
        files = list(self.config.download_dir.glob('*'))
        if not files:
            print("\033[90mNo files found\033[0m")
        else:
            print("\033[90mNo. | File Name                     | Size       | Modified\033[0m")
            print("\033[90m" + "-" * 80 + "\033[0m")
            
            for i, f in enumerate(sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:20], 1):
                size_mb = f.stat().st_size / (1024*1024)
                modified = datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                name = f.name[:30] + "..." if len(f.name) > 30 else f.name
                
                print(f"{i:3d} | {name:30s} | {size_mb:6.1f} MB | {modified}")
        
        print()
        input("\033[90mPress Enter to continue...\033[0m")
    
    def settings(self):
        while True:
            self.print_header()
            print("\033[36m⚙️ Settings\033[0m")
            print()
            
            print(f"1. 📁 Download Directory: {self.config.download_dir}")
            print(f"2. 🌐 Web Server Port: {self.config.web_port}")
            print(f"3. 🎨 Theme: {self.config.data['theme']}")
            print(f"4. 📥 Auto-open browser: {'Yes' if self.config.data['auto_open_browser'] else 'No'}")
            print(f"5. 💾 Save Settings")
            print(f"0. ↩️ Back")
            print()
            
            choice = input("\033[36mSelect option: \033[0m").strip()
            
            if choice == '1':
                print(f"\nCurrent: {self.config.download_dir}")
                print("Enter new directory (or press Enter to keep current):")
                new_dir = input("> ").strip()
                if new_dir:
                    try:
                        new_path = Path(new_dir)
                        new_path.mkdir(exist_ok=True, parents=True)
                        self.config.download_dir = new_path
                        print("\033[32m✅ Updated!\033[0m")
                    except Exception as e:
                        print(f"\033[31m❌ Error: {e}\033[0m")
            elif choice == '2':
                try:
                    new_port = int(input("New port (1024-65535): ").strip())
                    if 1024 <= new_port <= 65535:
                        self.config.web_port = new_port
                        self.config.data['web_port'] = new_port
                        print("\033[32m✅ Updated!\033[0m")
                    else:
                        print("\033[31m❌ Invalid port\033[0m")
                except:
                    print("\033[31m❌ Invalid number\033[0m")
            elif choice == '3':
                themes = ['dark', 'light', 'blue', 'green']
                print("Available themes:", ', '.join(themes))
                theme = input("Theme: ").strip()
                if theme in themes:
                    self.config.data['theme'] = theme
                    print("\033[32m✅ Updated!\033[0m")
            elif choice == '4':
                self.config.data['auto_open_browser'] = not self.config.data['auto_open_browser']
                print(f"\033[32m✅ Auto-open: {'On' if self.config.data['auto_open_browser'] else 'Off'}\033[0m")
            elif choice == '5':
                if self.config.save():
                    print("\033[32m✅ Settings saved!\033[0m")
                else:
                    print("\033[31m❌ Failed to save settings\033[0m")
                time.sleep(1)
                break
            elif choice == '0':
                break
            
            time.sleep(1)
    
    def statistics(self):
        self.print_header()
        print("\033[36m📊 Statistics\033[0m")
        print()
        
        total = len(self.engine.history)
        successful = sum(1 for h in self.engine.history if h['success'])
        failed = total - successful
        total_size = sum(h.get('size', 0) for h in self.engine.history) / (1024*1024*1024)      
        
        print(f"\033[33m📥 Total Downloads: {total}\033[0m")
        print(f"\033[32m✅ Successful: {successful}\033[0m")
        print(f"\033[31m❌ Failed: {failed}\033[0m")
        print(f"\033[34m💾 Total Size: {total_size:.2f} GB\033[0m")
        
        if total > 0:
            success_rate = (successful / total) * 100
            print(f"\033[36m📈 Success Rate: {success_rate:.1f}%\033[0m")
            
                           
            if self.engine.history:
                last = self.engine.history[-1]
                last_time = datetime.fromisoformat(last['timestamp']).strftime('%Y-%m-%d %H:%M')
                print(f"\n\033[90m🕐 Last download: {last_time}\033[0m")
                print(f"\033[90m📄 File: {last.get('filename', 'N/A')}\033[0m")
        
        print()
        input("\033[90mPress Enter to continue...\033[0m")

                                                           
def main():
    """Main application entry point"""
    
    print("\033[36m" + "═" * 60)
    print("   🚀 iOS DUAL MODE DOWNLOADER")
    print("   Terminal + Web Interface")
    print("   Compatible with a-Shell on iOS")
    print("═" * 60 + "\033[0m")
    
                        
    missing = []
    try:
        import flask
    except ImportError:
        missing.append('flask')
    try:
        import flask_socketio
    except ImportError:
        missing.append('flask-socketio')
    try:
        import yt_dlp
    except ImportError:
        missing.append('yt-dlp')
    try:
        import requests
    except ImportError:
        missing.append('requests')
    
    if missing:
        print(f"\033[33m⚠️  Missing dependencies: {', '.join(missing)}\033[0m")
        print("Install with: pip3 install " + " ".join(missing))
        web_required = any(m in missing for m in ['flask', 'flask-socketio'])
        core_required = any(m in missing for m in ['yt-dlp', 'requests'])
        if core_required:
            print("\033[31m❌ Core dependencies missing — cannot continue.\033[0m")
            sys.exit(1)
        print("Continue with terminal-only mode? (y/n): ", end='')
        if input().lower() != 'y':
            sys.exit(1)
    else:
        print("✓ All dependencies found")
    
                
    print("\n🔧 Initializing...")
    config = Config()
    print(f"✓ Download directory: {config.download_dir}")
    
    engine = DownloadEngine(config)
    print(f"✓ Loaded {len(engine.history)} history entries")
    
                                                               
    args = sys.argv[1:]
                                                         
    flags = [a for a in args if a.startswith('--')]
    pos = [a for a in args if not a.startswith('--')]
    
    if '--help' in flags or '-h' in flags:
        print("\n\033[36m⚡ Quick shortcuts:\033[0m")
        print("  python3 duel-downloader.py <URL>             ভিডিও+অডিও লিস্ট + best download")
        print("  python3 duel-downloader.py <URL> 360p        সরাসরি 360p download")
        print("  python3 duel-downloader.py <URL> 480p        সরাসরি 480p download")
        print("  python3 duel-downloader.py <URL> 720p        সরাসরি 720p download")
        print("  python3 duel-downloader.py <URL> 1080p       সরাসরি 1080p download")
        print("  python3 duel-downloader.py <URL> audio       audio-only download (mp4/m4a)")
        print("\n\033[33mFlags: --port PORT  --terminal-only\033[0m")
        sys.exit(0)
    
    if pos and (pos[0].startswith('http://') or pos[0].startswith('https://')):
        url = pos[0]
        shortcut_mode = 'best'
        if len(pos) > 1:
            arg2 = pos[1].lower()
            if arg2 in ('audio', 'mp3', 'music'):
                shortcut_mode = 'audio'
            elif arg2 in ('360p', '480p', '720p', '1080p', 'best', 'mp4', 'webm', 'worst'):
                shortcut_mode = arg2
            else:
                print(f"\033[33m⚠️ অজানা option '{pos[1]}' — best quality-তে download হবে\033[0m")
        
        terminal = TerminalInterface(engine, config)
        print("\n\033[36m🌐 Web UI এ background-ে চলছে (অন্য ডিভাইস থেকেও access করা যাবে)\033[0m")
        web_interface = WebInterface(engine, config)
        web_thread = threading.Thread(target=web_interface.start, daemon=True)
        web_thread.start()
        time.sleep(1.5)
        terminal.quick_download(url, shortcut_mode)
        
                                                                        
        did = None
        last_status = None
        for i in range(2):
            time.sleep(1)                               
        max_wait = 600            
        for _ in range(max_wait // 2):
            time.sleep(2)
            with engine._lock:
                vals = list(engine.active_downloads.values())
            cur = vals[-1].get('status') if vals else None
            if cur != last_status:
                v = vals[-1] if vals else {}
                prog = v.get('progress', 0)
                spd = v.get('speed', '0 KB/s')
                eta = v.get('eta', '--:--')
                name = v.get('filename') or '...'
                print(f"\r\033[90m  ⏳ {prog:.0f}% | {spd} | ETA {eta} | {name}\033[0m", end='', flush=True)
                last_status = cur
            if cur in ('completed', 'failed'):
                v = vals[-1] if vals else {}
                print()                     
                if cur == 'completed':
                    print(f"\n\033[32m🎉 Download completed: {v.get('filename')} ({TerminalInterface._size(v.get('filesize', 0))})\033[0m")
                else:
                    print(f"\n\033[31m❌ Download failed: {v.get('error', 'Unknown error')}\033[0m")
                break
        if last_status not in ('completed', 'failed'):
            print("\n\033[90m⏳ Background-ে download চলছে... Web UI-তে দেখতে পারবেন\033[0m")
        sys.exit(0)
    
    print("\n\033[33mModes:\033[0m")
    print("  1. 📟 Terminal Interface (in a-Shell)")
    print("  2. 🌐 Web Interface (in browser)")
    print("  3. 🚀 Both (Terminal + Web Server)")
    print()
    
    try:
        mode = input("\033[36mSelect mode (1/2/3): \033[0m").strip()
    except EOFError:
        print("\n\033[90m⚠️ No input received — starting mode 3 (Terminal + Web) by default\033[0m")
        mode = '3'
    
    if mode == '1':
                       
        print("\n📟 Starting Terminal Interface...")
        terminal = TerminalInterface(engine, config)
        terminal.main_menu()
    
    elif mode == '2':
                  
        print("\n🌐 Starting Web Interface...")
        web_interface = WebInterface(engine, config)
        web_interface.start()
    
    elif mode == '3':
                               
        print("\n🚀 Starting both Terminal and Web interface...")
        
                                        
        web_interface = WebInterface(engine, config)
        web_thread = threading.Thread(target=web_interface.start, daemon=True)
        web_thread.start()
        
        time.sleep(2)                                 
        
                                  
        terminal = TerminalInterface(engine, config)
        terminal.main_menu()
    
    else:
        print("\033[31m❌ Invalid selection\033[0m")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n\033[33m👋 Goodbye!\033[0m")
    except Exception as e:
        print(f"\n\033[31m❌ Error: {e}\033[0m")
        import traceback
        traceback.print_exc()
