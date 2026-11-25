"""Web server (standard library only).

    GET  /                    app shell: tabs Settings · Runs · Run · Architecture
    GET  /architecture        docs/architecture.mmd drawn with Mermaid
    GET  /run/<name>          one run's page (report skill); ?embed=1 inside the Run tab
    GET  /api/app             {title, settings}
    POST /api/runs            {settings} -> {run}   (400 with the reason if a setting is invalid)
    GET  /api/runs            past runs, newest first
    GET  /api/runs/<name>     config, status, results and log of one run
    GET  /health              ok   (not /healthz: Cloud Run reserves it)

python -m app [--port 8080] [--host 127.0.0.1]   (Cloud Run sets PORT; the container listens on 0.0.0.0)
"""
from __future__ import annotations

import argparse
import html
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import page, runner, runs

STATIC = Path(__file__).with_name("static")
ARCH = runs.ROOT / "docs" / "architecture.mmd"
MAX_BODY = 1 << 20


def coerce(settings: dict) -> dict:
    """Settings from the browser -> typed values, checked against runner.SETTINGS. Raises ValueError."""
    out = {}
    for s in runner.SETTINGS:
        name, kind = s["name"], s.get("type", "text")
        v = settings.get(name, s.get("default"))
        try:
            if kind == "int":
                v = int(v)
            elif kind == "float":
                v = float(v)
            elif kind == "bool":
                v = v if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes", "on")
            else:
                v = "" if v is None else str(v).strip()
        except (TypeError, ValueError):
            raise ValueError(f"{s.get('label', name)}: not a valid {kind}") from None
        if kind in ("int", "float"):
            if "min" in s and v < s["min"] or "max" in s and v > s["max"]:
                raise ValueError(f"{s.get('label', name)}: must be between {s.get('min', '-inf')} and {s.get('max', 'inf')}")
        if kind == "choice" and v not in s.get("options", []):
            raise ValueError(f"{s.get('label', name)}: must be one of {', '.join(map(str, s.get('options', [])))}")
        if kind == "text" and s.get("required") and not v:
            raise ValueError(f"{s.get('label', name)}: required")
        out[name] = v
    return out


def architecture_page() -> str:
    src = ARCH.read_text(encoding="utf-8") if ARCH.exists() else "flowchart LR\n  A[docs/architecture.mmd is missing]"
    return (STATIC / "architecture.html").read_text(encoding="utf-8").replace("<!--MERMAID-->", html.escape(src))


class Handler(BaseHTTPRequestHandler):
    server_version = "gcp-web-ui-app"

    def log_message(self, fmt, *args):  # one short line per request on stderr (Cloud Run collects it)
        if os.environ.get("QUIET") != "1":
            super().log_message(fmt, *args)

    def send(self, code: int, body, ctype: str = "application/json; charset=utf-8") -> None:
        data = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        p, q = u.path.rstrip("/") or "/", parse_qs(u.query)
        if p == "/":
            return self.send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        if p == "/health":
            return self.send(200, "ok", "text/plain; charset=utf-8")
        if p == "/architecture":
            return self.send(200, architecture_page(), "text/html; charset=utf-8")
        if p == "/api/app":
            return self.send(200, {"title": runner.TITLE, "settings": runner.SETTINGS})
        if p == "/api/runs":
            return self.send(200, runs.listing())
        if p.startswith("/api/runs/"):
            d = runs.find(p.rsplit("/", 1)[1])
            return self.send(200, runs.info(d, full=True)) if d else self.send(404, {"error": "no such run"})
        if p.startswith("/run/"):
            d = runs.find(p.rsplit("/", 1)[1])
            if not d:
                return self.send(404, "<p>No such run.</p>", "text/html; charset=utf-8")
            return self.send(200, page.render(d, embed="embed" in q), "text/html; charset=utf-8")
        if p == "/favicon.ico":
            return self.send(204, b"", "image/x-icon")
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if urlparse(self.path).path.rstrip("/") != "/api/runs":
            return self.send(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            return self.send(413, {"error": "request too large"})
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
            settings = coerce(body.get("settings") or {})
        except ValueError as ex:
            return self.send(400, {"error": str(ex) or "invalid JSON"})
        d = runs.start(runner.run, settings, on_done=page.write)
        self.send(HTTPStatus.ACCEPTED, {"run": d.name})


def make_server(host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    s = ThreadingHTTPServer((host, port), Handler)
    s.daemon_threads = True
    return s


def main(argv=None) -> None:
    a = argparse.ArgumentParser(description="Web UI app")
    a.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    a.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8080)))
    args = a.parse_args(argv)
    s = make_server(args.host, args.port)
    print(f"{runner.TITLE}: http://{args.host}:{args.port}/   runs in {runs.runs_dir()}", flush=True)
    try:
        s.serve_forever()
    except KeyboardInterrupt:
        pass
