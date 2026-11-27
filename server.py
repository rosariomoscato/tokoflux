"""Tokoflux local server. Requires only the Python standard library."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
from threading import Lock, Thread, Timer
from time import perf_counter
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler, Request
import uuid
import webbrowser

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "frontend" / "dist"
OLLAMA = "http://127.0.0.1:11434"
DB = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "Tokoflux" / "history.sqlite3"
VERSION = "0.1.1"
PROMPT = ("Write a Python function that merges closed overlapping intervals without "
          "mutating its input. Include four unittest cases: empty input, unsorted "
          "intervals, touching endpoints, and separate intervals. Return code only.")
CONTEXT = 8192
MAX_TOKENS = 2048
ALLOWED_CONTEXTS = (2048, 4096, 8192, 16384, 32768)
OPENER = build_opener(ProxyHandler({}))
LOCK = Lock()
JOB = {"status": "idle", "model": None, "error": None}
SERVER = None


def upstream(path, data=None, timeout=5):
    body = json.dumps(data).encode() if data is not None else None
    return OPENER.open(Request(OLLAMA + path, data=body,
                               headers={"Content-Type": "application/json"}), timeout=timeout)


def ollama_json(path, data=None, timeout=5):
    with upstream(path, data, timeout) as response:
        return json.load(response)


def ollama_models():
    return [{"name": item["name"], "size": item.get("size", 0)}
            for item in ollama_json("/api/tags")["models"]
            if not (item.get("remote_host") or item.get("remote_model")
                    or item["name"].endswith((":cloud", "-cloud")))]


def installed_models():
    return [item["name"] for item in ollama_models()]


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB)


def migrate(db):
    columns = {row[1] for row in db.execute("PRAGMA table_info(runs)")}
    if "session" not in columns:
        db.execute("ALTER TABLE runs ADD COLUMN session TEXT")
    if "position" not in columns:
        db.execute("ALTER TABLE runs ADD COLUMN position INTEGER")


def history():
    with closing(connect()) as db:
        runs = []
        for id_, session, position, payload in db.execute(
                "SELECT id, session, position, payload FROM runs ORDER BY id DESC LIMIT 100"):
            run = json.loads(payload)
            run.update(id=id_, session=session, position=position)
            runs.append(run)
        return runs


def save(run, session, position):
    with closing(connect()) as db, db:
        db.execute("INSERT INTO runs (payload, session, position) VALUES (?, ?, ?)",
                   (json.dumps(run), session, position))


def clear_history():
    with closing(connect()) as db, db:
        db.execute("DELETE FROM runs")


def shutdown_server():
    if SERVER is not None:
        SERVER.shutdown()


def rate(tokens, ns):
    return round(tokens * 1e9 / ns, 2) if ns and tokens is not None else None


def benchmark(models, mode, session, context):
    options = {"num_ctx": context, "num_predict": MAX_TOKENS, "temperature": 0}
    try:
        for position, model in enumerate(models):
            with LOCK:
                JOB.update(model=model)
            request = {"model": model, "options": options, "stream": False}
            if mode == "cold":
                ollama_json("/api/generate", {**request, "keep_alive": 0}, 120)
            else:
                ollama_json("/api/generate", {**request, "keep_alive": "5m"}, 120)
            start, first, final = perf_counter(), None, None
            request.update(prompt=PROMPT, stream=True, keep_alive="5m")
            with upstream("/api/generate", request, 300) as response:
                for line in response:
                    packet = json.loads(line)
                    if packet.get("error"):
                        raise ValueError(packet["error"])
                    if first is None and (packet.get("response") or packet.get("thinking")):
                        first = round(perf_counter() - start, 3)
                    if packet.get("done"):
                        final = packet
                        break
            if final is None:
                raise ValueError("Incomplete Ollama response")
            elapsed = round(perf_counter() - start, 3)
            try:
                active = next((item for item in ollama_json("/api/ps")["models"]
                               if item["name"] == model), {})
            except (OSError, ValueError, KeyError):
                active = {}
            size, vram = active.get("size"), active.get("size_vram")
            prompt_tokens = final.get("prompt_eval_count")
            cached = final.get("prompt_eval_cached_count")
            # Ollama versions exposing a separate cache counter report newly evaluated
            # tokens in prompt_eval_count. Legacy versions expose only that count.
            save({
                "date": datetime.now(timezone.utc).isoformat(), "model": model,
                "mode": mode, "first": first, "total": elapsed,
                "load": round(final["load_duration"] / 1e9, 3) if "load_duration" in final else None,
                "prompt": rate(prompt_tokens, final.get("prompt_eval_duration")),
                "decode": rate(final.get("eval_count"), final.get("eval_duration")),
                "cached": cached, "gpu": round(100 * vram / size) if size and vram is not None else None,
                "context": active.get("context_length"), "tokens": final.get("eval_count"),
                "stop": final.get("done_reason"),
            }, session, position)
        with LOCK:
            JOB.update(status="complete", model=None)
    except Exception as error:
        print(f"Benchmark error: {error}", flush=True)
        with LOCK:
            JOB.update(status="error", error="benchmark_failed")


class Handler(SimpleHTTPRequestHandler):
    def json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        return self.headers.get("Host") in {
            f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"
        }

    def list_directory(self, path):
        self.send_error(404)
        return None

    def do_GET(self):
        if not self.valid_host():
            return self.send_error(403)
        path = urlsplit(self.path).path
        if path == "/api/health":
            return self.json({"app": "Tokoflux", "version": VERSION})
        if path == "/api/prompt":
            return self.json({"prompt": PROMPT})
        if path == "/api/status":
            try:
                models = ollama_models()
                running = ollama_json("/api/ps")["models"]
                return self.json({"online": True, "models": models, "running": running})
            except (OSError, ValueError, KeyError):
                return self.json({"online": False, "models": [], "running": []})
        if path == "/api/benchmarks":
            with LOCK:
                job = JOB.copy()
            return self.json({"job": job, "runs": history()})
        return super().do_GET()

    def do_POST(self):
        path = urlsplit(self.path).path
        if path == "/api/shutdown":
            if not self.valid_host() or self.headers.get("Origin") != f"http://{self.headers.get('Host')}":
                return self.json({"error": "invalid_origin"}, 403)
            self.json({"stopping": True})
            Timer(0.3, shutdown_server).start()
            return
        if path == "/api/history/clear":
            if not self.valid_host() or self.headers.get("Origin") != f"http://{self.headers.get('Host')}":
                return self.json({"error": "invalid_origin"}, 403)
            clear_history()
            return self.json({"cleared": True})
        if path != "/api/benchmarks":
            return self.json({"error": "not_found"}, 404)
        if not self.valid_host() or self.headers.get("Origin") != f"http://{self.headers.get('Host')}":
            return self.json({"error": "invalid_origin"}, 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 2048:
                raise ValueError()
            data = json.loads(self.rfile.read(length))
            models, mode = data["models"], data["mode"]
            context = data.get("context", CONTEXT)
            if (not isinstance(models, list) or not 1 <= len(models) <= 2
                    or any(not isinstance(model, str) or not model for model in models)
                    or len(set(models)) != len(models) or mode not in ("warm", "cold")
                    or context not in ALLOWED_CONTEXTS):
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            return self.json({"error": "invalid_selection"}, 400)
        with LOCK:
            if JOB["status"] == "running":
                return self.json({"error": "already_running"}, 409)
            try:
                installed = set(installed_models())
            except (OSError, ValueError, KeyError):
                return self.json({"error": "ollama_offline"}, 503)
            if not set(models) <= installed:
                return self.json({"error": "model_missing"}, 400)
            JOB.update(status="running", model=models[0], error=None)
            Thread(target=benchmark, args=(models, mode, str(uuid.uuid4()), context), daemon=True).start()
        return self.json({"accepted": True}, 202)

    def log_message(self, fmt, *args):
        if not self.path.startswith("/api/"):
            super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    url = f"http://127.0.0.1:{args.port}"
    if not (DIST / "index.html").is_file():
        raise SystemExit("Frontend build missing. Run npm ci and npm run build in frontend.")
    with closing(connect()) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
        migrate(db)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, directory=str(DIST)))
    except OSError:
        try:
            with OPENER.open(url + "/api/health", timeout=2) as response:
                already_running = json.load(response).get("app") == "Tokoflux"
        except (OSError, ValueError):
            already_running = False
        if not already_running:
            raise SystemExit(f"Port {args.port} is unavailable.")
        if not args.no_browser:
            webbrowser.open(url)
        return
    global SERVER
    SERVER = server
    print(f"Tokoflux · {url}", flush=True)
    if not args.no_browser:
        Timer(0.25, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    print("Tokoflux arrestato.", flush=True)


if __name__ == "__main__":
    main()
