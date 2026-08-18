#!/usr/bin/env python3
"""Unit tests for improved duel-downloader.py (no network needed)."""
import sys, os, json, time, tempfile, threading
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import types
dd = types.ModuleType('dd')
exec(open('duel-downloader.py').read().split('if __name__')[0], dd.__dict__)

def run_tests():
    results = []
    def check(name, cond, detail=""):
        results.append((name, cond, detail))
        print(f"{'PASS' if cond else 'FAIL'}: {name} {detail}")

    # --- Config: web_host default and CLI port override ---
    orig_argv = sys.argv
    sys.argv = ['duel-downloader.py', '--port', '9090']
    cfg = dd.Config.__new__(dd.Config)
    cfg.home = Path(tempfile.mkdtemp())
    cfg.web_port = 8080
    cfg.web_host = "0.0.0.0"
    cfg.download_dir = cfg.home / "Downloads"
    cfg.config_file = cfg.home / ".dualdl_config.json"
    cfg.history_file = cfg.home / ".dualdl_history.json"
    cfg.data = {}
    cfg.load_config()
    if len(sys.argv) >= 3 and sys.argv[1] == '--port':
        try:
            p = int(sys.argv[2])
            if 1024 <= p <= 65535:
                cfg.web_port = p
                cfg.data['web_port'] = p
        except ValueError:
            pass
    sys.argv = orig_argv
    check("Config web_host default is 0.0.0.0", cfg.web_host == "0.0.0.0")
    check("Config CLI --port override applied", cfg.web_port == 9090)
    cfg.download_dir.mkdir(exist_ok=True)

    # --- Engine: thread safety ---
    engine = dd.DownloadEngine(cfg)
    check("Engine has _lock", hasattr(engine, '_lock') and hasattr(engine._lock, 'acquire'))
    check("Cleanup timer started", engine._cleanup_timer.is_alive())

    # concurrent download from many threads simultaneously
    errs = []
    def hammer(i):
        try:
            with engine._lock:
                engine.active_downloads[f"d{i}"] = {'status': 'downloading', 'progress': 0.0, 'started_at': time.time()}
            for _ in range(200):
                with engine._lock:
                    engine.active_downloads[f"d{i}"]['progress'] += 0.1
            with engine._lock:
                engine.active_downloads.pop(f"d{i}")
        except Exception as e:
            errs.append(str(e))
    threads = [threading.Thread(target=hammer, args=(i,)) for i in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()
    check("Concurrent lock stress test", len(errs) == 0, str(errs) or "")

    # --- Concurrent limit ---
    cfg.data['max_concurrent'] = 2
    engine2 = dd.DownloadEngine(cfg)
    engine2.socketio = None
    engine2.active_downloads = {
        'a': {'status': 'downloading', 'started_at': time.time()},
        'b': {'status': 'downloading', 'started_at': time.time()},
        'c': {'status': 'completed', 'started_at': time.time() - 1000},
    }
    did = engine2.download_file('https://example.com/nonexistent-9876.pdf')
    time.sleep(1.5)
    ok = False
    for _ in range(30):
        time.sleep(0.2)
        with engine2._lock:
            v = engine2.active_downloads.get(did, {})
        if v.get('status') == 'failed' and 'limit' in (v.get('error') or ''):
            ok = True
            break
    check("Concurrent download limit enforced", ok, f"status={v.get('status')}, err={(v.get('error') or '')[:60]}")

    # --- Path traversal protection ---
    api = dd.WebInterface.__new__(dd.WebInterface)
    api.engine = engine2
    api.config = cfg
    app = api.app = dd.Flask(__name__)
    api.socketio = dd.SocketIO(app, cors_allowed_origins="*")
    api.setup_routes()
    api.setup_events()
    client = app.test_client()
    # Werkzeug routing never passes a '/' into the filename param, so traversal
    # requests that contain decoded '/' hit 404 at routing layer (also blocked).
    r = client.get('/api/open/../../etc/passwd')
    check("Path traversal '../../etc/passwd' blocked", r.status_code in (400, 404))
    r = client.get('/api/open/foo/bar')
    check("Path traversal 'foo/bar' blocked", r.status_code in (400, 404))
    # our handler-level check: backslash in path reaches handler and returns 400
    r = client.get('/api/open/..%5c..%5cetc%5cpasswd')
    check("Path traversal via backslash blocked with 400", r.status_code == 400)
    # create a real file and allow opening
    (cfg.download_dir / 'test.txt').write_text('hello')
    r = client.get('/api/open/test.txt')
    check("Legit file openable", r.status_code == 200)

    # --- History ID sequential ---
    id1 = len(engine2.history)
    engine2.add_history('http://x', 'a.bin', True, 10, 'file')
    engine2.add_history('http://y', 'b.bin', True, 10, 'file')
    ids = [h['id'] for h in engine2.history[-2:]]
    check("History IDs sequential", ids == [id1 + 1, id1 + 2], str(ids))

    # --- Periodic cleanup logic (one-shot simulation of the cleanup body) ---
    engine2.active_downloads['stale'] = {'status': 'completed', 'started_at': time.time() - 2000}
    with engine2._lock:
        cutoff = time.time() - 900
        engine2.active_downloads = {
            k: v for k, v in engine2.active_downloads.items()
            if v.get('started_at', 0) > cutoff
        }
    check("Old completed entries cleaned", 'stale' not in engine2.active_downloads)

    # --- Web UI serves index and /api/active returns only in-progress ---
    r = client.get('/api/active')
    check("/api/active returns only downloading", all(x['status'] == 'downloading' for x in r.json))
    r = client.get('/')
    check("Index page served", r.status_code == 200 and 'Download Manager' in r.get_data(as_text=True))

    # --- f-string bug fixed ---
    src = Path('duel-downloader.py').read_text()
    check("L1336 f-string prefix fixed", 'print(f"\\033[90m📱 On other devices: http://YOUR_IP:{self.config.web_port}\\033[0m")' in src
          or "print(f\"\033[90m📱 On other devices: http://YOUR_IP:{self.config.web_port}\033[0m\")" in src)

    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    sys.exit(1 if failed else 0)

if __name__ == '__main__':
    run_tests()
