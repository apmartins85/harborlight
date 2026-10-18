"""Harborlight Tasks — MIT licensed, dependency-free HTTP microservice."""
import json
import os
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

TASKS = {}
LOCK = threading.Lock()
MAX_BODY = 4096
MAX_TASKS = 1000


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/healthz':
            return self.reply(200, {'service': 'harborlight-tasks', 'status': 'ok'})
        if path == '/':
            return self.reply(200, {'service': 'harborlight-tasks', 'license': 'MIT',
                                    'endpoints': ['GET /healthz', 'GET /tasks', 'POST /tasks', 'DELETE /tasks/{id}']})
        if path == '/tasks':
            with LOCK:
                tasks = [dict(t) for t in TASKS.values()]
            return self.reply(200, {'tasks': tasks})
        self.reply(404, {'error': 'Not found'})

    def do_POST(self):
        if urlsplit(self.path).path != '/tasks':
            return self.reply(404, {'error': 'Not found'})
        # Chunked bodies are unsupported; close rejected connections.
        self.close_connection = True
        if self.headers.get('Transfer-Encoding'):
            return self.reply(400, {'error': 'Use Content-Length'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self.reply(400, {'error': 'Invalid Content-Length'})
        if size <= 0 or size > MAX_BODY:
            return self.reply(413, {'error': 'Body must contain 1 to 4096 bytes'})
        if self.headers.get_content_type() != 'application/json':
            return self.reply(415, {'error': 'Use application/json'})
        try:
            data = json.loads(self.rfile.read(size))
        except (ValueError, UnicodeError):
            return self.reply(400, {'error': 'Invalid JSON'})
        title = data.get('title') if isinstance(data, dict) else None
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            return self.reply(400, {'error': 'title must contain 1 to 200 characters'})
        task = {'id': str(uuid.uuid4()), 'title': title.strip()}
        with LOCK:
            if len(TASKS) >= MAX_TASKS:
                return self.reply(409, {'error': 'Task limit reached; delete a task first'})
            TASKS[task['id']] = task
        self.reply(201, task)

    def do_DELETE(self):
        path = urlsplit(self.path).path
        if not path.startswith('/tasks/'):
            return self.reply(404, {'error': 'Not found'})
        with LOCK:
            task = TASKS.pop(path[len('/tasks/'):], None)
        if task is None:
            return self.reply(404, {'error': 'Task not found'})
        self.reply(200, {'deleted': task['id']})

    def setup(self):
        super().setup()
        self.connection.settimeout(5)


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', int(os.environ.get('PORT', '8080'))), Handler).serve_forever()
