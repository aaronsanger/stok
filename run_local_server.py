"""
Zero-Docker Workstation Server & CLI Runner for [STOK].
Usage on workstation without Docker:
  - Web UI (http://127.0.0.1:8080):
      python run_local_server.py
  - CLI test:
      python run_local_server.py --cmd "[STOK] 219602 WAFER FLAT"
      python run_local_server.py --cmd "[STOK] WAFER STICK"
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from stok_service import BASE_DIR, StokEngine

engine = StokEngine(BASE_DIR)


class StokWorkbenchHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(404, "File not found")
            return
        ctype, _ = mimetypes.guess_type(str(path))
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path

        if route in ("/", "/index.html"):
            self._send_file(BASE_DIR / "templates" / "stok_workbench.html")
            return

        if route.startswith("/static/"):
            rel = Path(unquote(route[len("/static/") :])).name
            self._send_file(BASE_DIR / "static" / rel)
            return

        if route.rstrip("/") == "/api/stok":
            qs = parse_qs(parsed.query)
            q = (qs.get("q") or qs.get("command") or ["[STOK] 219602 WAFER FLAT"])[0]
            self._send_json(engine.run_stok_command(q))
            return

        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/")
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw_body.decode("utf-8", errors="ignore") or "{}")
        except Exception:
            body = {}

        if route == "/api/stok":
            cmd = str(body.get("command") or body.get("message") or body.get("q") or "[STOK] 219602 WAFER FLAT")
            self._send_json(engine.run_stok_command(cmd))
            return

        self.send_error(404, "Not found")


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone [STOK] Runner (No Docker)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Bind port (default: 8080)")
    parser.add_argument("--cmd", default="", help='Run a single command in terminal, e.g. "[STOK] 219602 WAFER FLAT"')
    args = parser.parse_args()

    if args.cmd:
        res = engine.run_stok_command(args.cmd.strip())
        print(res["reply_message"])
        return

    server = ThreadingHTTPServer((args.host, args.port), StokWorkbenchHandler)
    print(f"[STOK] Workstation Server running (No Docker) at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
