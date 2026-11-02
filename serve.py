"""Open the AI's world in your browser while it lives on your PC.

    python serve.py            then visit http://localhost:8765
    python serve.py --lan      also let other devices on your Wi-Fi visit
"""
import json
import os
import sys
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(ROOT, "docs")
INBOX = os.path.join(DOCS, "world", "inbox")


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path not in ("/api/note", "/api/answer"):
            return self.send_error(404)
        try:
            length = min(int(self.headers.get("Content-Length", 0)), 20000)
            note = json.loads(self.rfile.read(length))
            text = str(note.get("text", "")).strip()
            if self.path == "/api/answer":   # answering one of his requests
                entry = {"answer_for": str(note.get("id", ""))[:10], "text": text[:800],
                         "decision": {"yes": "granted", "no": "declined", "later": "waiting"}.get(note.get("decision"), "answered")}
            elif not text:
                raise ValueError("empty note")
            else:
                entry = {"from": str(note.get("from") or "Visitor")[:60], "text": text[:2000]}
            os.makedirs(INBOX, exist_ok=True)
            with open(os.path.join(INBOX, f"{time.time_ns()}.json"), "w", encoding="utf-8") as f:
                json.dump(entry, f)
        except (ValueError, json.JSONDecodeError) as e:
            return self.send_error(400, str(e))
        self.send_response(204)
        self.end_headers()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    host = "0.0.0.0" if "--lan" in sys.argv else "127.0.0.1"
    server = ThreadingHTTPServer((host, 8765), partial(Handler, directory=DOCS))
    print(f"The world is open at http://localhost:8765  (Ctrl+C to close)")
    server.serve_forever()
