#!/usr/bin/env python3
"""Local review server for the candidate clips. Audio never leaves this machine.

  scripts/review.py [--port 8765]   then open http://127.0.0.1:8765

Decisions (keep / maybe / reject, event, note, start/end nudges) are saved to
work/review.json on every change. Nudging re-cuts the clip on the spot.
"""
import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cut  # noqa: E402

PAGE = Path(__file__).resolve().parent / "review.html"
EVENTS = ["session.start", "task.acknowledge", "task.complete", "task.error",
          "input.required", "resource.limit", "user.spam"]
FIELDS = {"status", "event", "note", "adj_start", "adj_end"}


def save_review(review):
    tmp = cut.REVIEW.with_suffix(".tmp")
    tmp.write_text(json.dumps(review, indent=2, sort_keys=True))
    tmp.replace(cut.REVIEW)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter console
        if not self.path.startswith("/clips/"):
            super().log_message(fmt, *args)

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            return self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if path == "/api/clips":
            return self.send(200, {"events": EVENTS, "clips": cut.load_candidates(), "review": cut.load_review()})
        if path.startswith("/clips/"):
            f = (cut.OUT / path[len("/clips/"):]).resolve()
            if f.parent == cut.OUT.resolve() and f.suffix == ".wav" and f.exists():
                return self.send(200, f.read_bytes(), "audio/wav")
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/review":
            return self.send(404, {"error": "not found"})
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        rows = {r["n"]: r for r in cut.load_candidates()}
        n = body.get("n")
        if n not in rows:
            return self.send(400, {"error": f"unknown clip {n!r}"})

        review = cut.load_review()
        entry = review.get(n, {})
        before = (entry.get("adj_start", 0.0), entry.get("adj_end", 0.0))
        entry.update({k: v for k, v in body.items() if k in FIELDS})
        after = (entry.get("adj_start", 0.0), entry.get("adj_end", 0.0))
        if after != before:
            try:
                cut.cut(rows[n], *after)
            except Exception as e:  # keep old nudges if the re-cut fails
                return self.send(400, {"error": str(e)})
        review[n] = entry
        save_review(review)
        self.send(200, {"ok": True, "entry": entry, "recut": after != before})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Review page: http://127.0.0.1:{args.port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
