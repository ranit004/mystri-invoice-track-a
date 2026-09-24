import json
import logging
import sqlite3
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit
from . import importing, reporting, storage

logger = logging.getLogger(__name__)

RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW = 60

_ip_request_times = defaultdict(list)


def check_rate_limit(ip):
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW
    timestamps = [t for t in _ip_request_times[ip] if t > cutoff]
    _ip_request_times[ip] = timestamps
    if len(timestamps) >= RATE_LIMIT_REQUESTS:
        retry_after = max(1, int(timestamps[0] + RATE_LIMIT_WINDOW - now))
        return False, retry_after
    timestamps.append(now)
    return True, 0


def make_server(db_path, web_dir, port):
    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body, content_type='application/json; charset=utf-8', extra_headers=None):
            if not isinstance(body, (bytes, str)):
                body = json.dumps(body)
            if isinstance(body, str):
                body = body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if extra_headers:
                for k, v in extra_headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlsplit(self.path)
            static = {'/': ('index.html', 'text/html; charset=utf-8'),
                      '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                      '/style.css': ('style.css', 'text/css; charset=utf-8')}
            if url.path in static:
                name, mime = static[url.path]
                return self.send(200, (web_dir / name).read_bytes(), mime)

            allowed, retry_after = check_rate_limit(self.client_address[0])
            if not allowed:
                return self.send(
                    429,
                    {'error': 'Too many requests, please slow down'},
                    extra_headers={'Retry-After': str(retry_after)}
                )

            db = storage.connect(db_path)
            try:
                if url.path == '/api/overview':
                    return self.send(200, reporting.overview(db))
                if url.path == '/api/invoices':
                    status = parse_qs(url.query).get('status', ['all'])[0]
                    return self.send(200, reporting.invoices(db, status))
                if url.path == '/api/export':
                    return self.send(200, reporting.export_csv(db), 'text/csv; charset=utf-8')
                return self.send(404, {'error': 'Not found'})
            except ValueError as exc:
                self.send(400, {'error': str(exc)})
            except Exception as exc:
                logger.exception("Unhandled GET request exception: %s", exc)
                self.send(500, {'error': 'An internal error occurred while processing the request'})
            finally:
                db.close()

        def do_POST(self):
            url = urlsplit(self.path)
            if url.path != '/api/import':
                return self.send(404, {'error': 'Not found'})

            allowed, retry_after = check_rate_limit(self.client_address[0])
            if not allowed:
                return self.send(
                    429,
                    {'error': 'Too many requests, please slow down'},
                    extra_headers={'Retry-After': str(retry_after)}
                )

            origin = self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',
                                         f'http://localhost:{self.server.server_port}'):
                return self.send(403, {'error': 'Use the local application page'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if size < 0 or size > 2 * 1024 * 1024:
                    raise ValueError('Use a CSV smaller than 2 MB')
                raw_bytes = self.rfile.read(size)
                text = raw_bytes.decode('utf-8-sig')
            except (ValueError, UnicodeDecodeError):
                return self.send(400, {'error': 'Use a UTF-8 CSV smaller than 2 MB'})
            db = storage.connect(db_path)
            try:
                kind = parse_qs(url.query).get('kind', [''])[0]
                filename = self.headers.get('X-Import-Filename')
                result = importing.import_csv(db, text, kind, filename=filename)
                self.send(200, result)
            except ValueError as exc:
                self.send(400, {'error': str(exc)})
            except sqlite3.IntegrityError as exc:
                logger.warning("Database integrity error during import: %s", exc, exc_info=True)
                self.send(400, {'error': 'A database constraint error occurred'})
            except Exception as exc:
                logger.exception("Unhandled POST import exception: %s", exc)
                self.send(500, {'error': 'An internal error occurred while processing the import request'})
            finally:
                db.close()

    return HTTPServer(('127.0.0.1', port), Handler)
