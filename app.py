"""Tiny status page. Python standard library only."""
import json
import os
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
CONFIG = Path(os.environ.get('SERVICES_FILE', str(ROOT / 'services.json')))
INTERVAL = max(5, int(os.environ.get('CHECK_INTERVAL', '15')))
TIMEOUT = 3
lock = threading.Lock()
state = {'updated_at': None, 'services': []}


def check(service):
    start = time.monotonic()
    code = None
    try:
        request = urllib.request.Request(service['url'], headers={'User-Agent': 'Harborlight/1.0'})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            code = response.status
        healthy = 200 <= code < 400
    except Exception:
        healthy = False
    return {'name': service['name'], 'status': 'operational' if healthy else 'down',
            'response_ms': round((time.monotonic() - start) * 1000), 'http_status': code}


def monitor(services):
    while True:
        with ThreadPoolExecutor(max_workers=min(8, len(services))) as pool:
            results = list(pool.map(check, services))
        with lock:
            state.update(updated_at=datetime.now(timezone.utc).isoformat(), services=results)
        time.sleep(INTERVAL)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path == '/healthz':
            body, kind = b'ok', 'text/plain'
        elif path == '/api/status':
            with lock:
                body = json.dumps(state).encode()
            kind = 'application/json'
        elif path == '/':
            body, kind = (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    services = json.loads(CONFIG.read_text())
    if not isinstance(services, list) or not services:
        raise ValueError('services.json must contain a nonempty list')
    for service in services:
        if not service.get('name') or not service.get('url', '').startswith(('http://', 'https://')):
            raise ValueError('Each service needs a name and an HTTP(S) URL')
    threading.Thread(target=monitor, args=(services,), daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0', int(os.environ.get('PORT', '8080'))), Handler).serve_forever()
