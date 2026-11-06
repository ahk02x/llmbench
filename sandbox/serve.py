#!/usr/bin/env python3
"""llmbench sandbox: chat with the models on the bench host from a browser. Stdlib only.

  ./sandbox/serve.py                 # http://127.0.0.1:8311, talks to bench.DEFAULT_HOST
  ./sandbox/serve.py --open          # and open it in the default browser
  ./sandbox/serve.py --port 9000 --host http://127.0.0.1:11434

Binds to localhost only. The page talks to this server, never to Ollama directly; it relays a short
allowlist of read + chat endpoints, so a stray web page cannot pull or delete models through it.
"""
import argparse, json, pathlib, sys, urllib.error, urllib.request, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import bench  # noqa: E402  (check(), DEFAULT_HOST)

RELAY = {"GET": {"/api/tags", "/api/ps", "/api/version"}, "POST": {"/api/chat", "/api/show"}}


def bench_summary():
    """Latest speed / fit / quality row per model from results/, for the model picker."""
    out = {}
    for f in sorted((ROOT / "results").glob("*.jsonl")):
        if f.stem.endswith("-ctx"):
            continue
        for line in f.read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            q = r.get("quality") or {}
            out[r["model"]] = {"tps": (r.get("short") or {}).get("gen_tps"), "vram_pct": r.get("vram_pct"),
                               "size_gb": r.get("size_gb"), "passed": q.get("passed"), "total": q.get("total"),
                               "ts": r.get("ts")}
    return out


def tasks():
    """tasks.json with prompts expanded exactly as bench_model() sends them."""
    ts = json.loads((ROOT / "tasks.json").read_text())
    for t in ts:
        if "haystack_needle" in t:
            t["prompt"] = t["prompt"].replace("{{HAYSTACK}}", bench.haystack(t["haystack_needle"]))
    return ts


def ladder_cfg():
    """Per-model think / num_ctx defaults the bench used (ladders.json)."""
    cfg = {}
    for group in json.loads((ROOT / "ladders.json").read_text()).values():
        for m in group:
            cfg[m["model"]] = {k: v for k, v in m.items() if k in ("think", "num_ctx", "max_tokens")}
    return cfg


class Handler(BaseHTTPRequestHandler):
    host = bench.DEFAULT_HOST

    def log_message(self, fmt, *args):
        if "/api/ps" not in self.path:
            sys.stderr.write("%s %s\n" % (self.log_date_time_string(), fmt % args))

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def same_origin(self):
        """POSTs must come from this page: custom header forces a CORS preflight, which we never grant."""
        origin = self.headers.get("Origin")
        return self.headers.get("X-Sandbox") == "1" and (origin is None or origin == f"http://{self.headers.get('Host')}")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            return self.send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/info":
            return self.send(200, {"host": self.host, "tasks": tasks(),
                                   "bench": bench_summary(), "cfg": ladder_cfg()})
        if path.startswith("/ollama/") and path[7:] in RELAY["GET"]:
            return self.relay(path[7:])
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if not self.same_origin():
            return self.send(403, {"error": "cross-origin request refused"})
        path = self.path.split("?")[0]
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if path == "/grade":
            req = json.loads(body or b"{}")
            task = next((t for t in tasks() if t["id"] == req.get("id")), None)
            if not task:
                return self.send(404, {"error": "unknown task"})
            return self.send(200, {"pass": bench.check(task["check"], req.get("text", "")), "check": task["check"]})
        if path.startswith("/ollama/") and path[7:] in RELAY["POST"]:
            return self.relay(path[7:], body)
        self.send(404, {"error": "not found"})

    def relay(self, path, body=None):
        """Pass Ollama's response through line by line, so streamed tokens reach the page as they arrive."""
        req = urllib.request.Request(self.host + path, data=body, headers={"Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req, timeout=900)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            try:
                detail = json.loads(detail).get("error", detail)
            except ValueError:
                pass
            return self.send(e.code, {"error": detail})
        except OSError as e:
            return self.send(502, {"error": f"bench host unreachable ({self.host}): {getattr(e, 'reason', e)}",
                                   "asleep": True})
        with r:
            self.send_response(200)
            self.send_header("Content-Type", r.headers.get("Content-Type", "application/json"))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()  # HTTP/1.0: no length, the body ends when the connection closes
            try:
                for line in r:
                    self.wfile.write(line)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass  # page pressed Stop; closing upstream makes Ollama stop generating


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default=bench.DEFAULT_HOST, help="Ollama base URL")
    ap.add_argument("--port", type=int, default=8311)
    ap.add_argument("--open", action="store_true", help="open the page in the default browser")
    a = ap.parse_args()
    Handler.host = a.host.rstrip("/")
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"llmbench sandbox on http://127.0.0.1:{a.port}  ->  {Handler.host}", flush=True)
    if a.open:
        webbrowser.open(f"http://127.0.0.1:{a.port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
