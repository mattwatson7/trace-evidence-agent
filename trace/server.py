"""Local HTTP boundary. No database, remote URLs or arbitrary file serving."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading
from urllib.parse import urlsplit

from trace.demo import DEMO
from trace.engine import investigate

WEB = Path(__file__).resolve().parent.parent / 'web'
ASSETS = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
          '/style.css': ('style.css', 'text/css'), '/favicon.svg': ('favicon.svg', 'image/svg+xml')}
SLOTS = threading.BoundedSemaphore(2)


class Handler(BaseHTTPRequestHandler):
    server_version = 'Trace/1.0'

    def setup(self):
        super().setup()
        self.connection.settimeout(8)

    def respond(self, status, data, content_type='application/json'):
        if status >= 400 and not getattr(self, '_body_read', False):
            # Closing a socket with unread request bytes can discard the response
            # on Windows. Drain only a small, explicitly bounded rejected body;
            # never wait on oversized, chunked, or slow input just to reject it.
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if 0 < length <= 65536 and not self.headers.get('Transfer-Encoding'):
                    self.connection.settimeout(.25)
                    self.rfile.read(length)
            except (ValueError, OSError):
                pass
            finally:
                self.connection.settimeout(8)
        if content_type == 'application/json':
            data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers()
        if self.command != 'HEAD':
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass  # Browser cancelled; no persistent state to roll back.

    def allowed_host(self):
        hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        if self.headers.get('Host') not in hosts:
            self.respond(403, {'error': 'Use the local Trace address.'})
            return False
        return True

    def do_GET(self):
        if not self.allowed_host():
            return
        path = urlsplit(self.path).path
        if path == '/api/health':
            self.respond(200, {'status': 'ok', 'version': '1.0.0', 'default_mode': 'extractive'})
        elif path == '/api/demo':
            self.respond(200, DEMO)
        elif path in ASSETS:
            filename, content_type = ASSETS[path]
            try:
                self.respond(200, (WEB / filename).read_bytes(), content_type)
            except OSError:
                self.respond(500, {'error': 'A bundled asset is missing. Check your installation.'})
        else:
            self.respond(404, {'error': 'Not found.'})

    do_HEAD = do_GET

    def do_POST(self):
        if not self.allowed_host():
            return
        if self.path != '/api/investigate':
            self.respond(404, {'error': 'Not found.'})
            return
        origin = self.headers.get('Origin')
        if origin is not None and origin not in {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}:
            self.respond(403, {'error': 'Cross-origin requests are not allowed.'})
            return
        if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            self.respond(415, {'error': 'Send application/json.'})
            return
        try:
            length = int(self.headers.get('Content-Length', ''))
            if length < 0 or self.headers.get('Transfer-Encoding'):
                raise ValueError()
        except ValueError:
            self.respond(400, {'error': 'A valid Content-Length is required; chunked bodies are unsupported.'})
            return
        if length > 2000000:
            self.respond(413, {'error': 'Request exceeds the 2 MB limit.'})
            return
        if not SLOTS.acquire(blocking=False):
            self.respond(429, {'error': 'Two investigations are already running. Try again shortly.'})
            return
        try:
            try:
                raw = self.rfile.read(length)
                self._body_read = True
                payload = json.loads(raw.decode('utf-8'))
            except (ValueError, UnicodeError) as exc:
                raise ValueError('Send valid UTF-8 JSON.') from exc
            if not isinstance(payload, dict):
                raise ValueError('The request must be a JSON object.')
            model = payload.get('model')
            if model is not None and (not isinstance(model, str) or not re.fullmatch(r'[\w][\w.:-]{0,119}', model)):
                raise ValueError('Use a local Ollama model name.')
            report = investigate(payload.get('question'), payload.get('documents'), model)
            self.respond(200, report)
        except ValueError as exc:
            self.respond(400, {'error': str(exc)})
        except (TimeoutError, OSError):
            self.respond(408, {'error': 'The request timed out or the connection closed. Try again.'})
        finally:
            SLOTS.release()

    def unsupported(self):
        self.respond(405, {'error': 'Method not allowed.'})

    do_PUT = do_DELETE = do_PATCH = do_OPTIONS = unsupported

    def log_message(self, *args):
        pass  # Do not log document content, questions or browser history.


def main():
    parser = argparse.ArgumentParser(description='Trace — local evidence investigation')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('port must be between 1 and 65535')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Trace is ready at http://127.0.0.1:{args.port} (Ctrl+C to stop)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
