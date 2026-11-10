"""Run the twin on this computer:  python tools/serve.py  ->  http://127.0.0.1:8765

Python's plain `http.server` answers one request at a time and drops big files on Windows (black ground, no sky).
This one is threaded, keeps connections alive and never caches, so edited files always reload.
"""
import functools
import http.server
import sys
from pathlib import Path


class NoCache(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *a):
        pass


port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
root = Path(__file__).resolve().parents[1]
print(f"GH-01 twin: http://127.0.0.1:{port}")
http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(NoCache, directory=str(root))).serve_forever()
