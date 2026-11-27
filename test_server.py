"""Tests for the Tokoflux server (stdlib unittest, no external dependencies)."""
import json
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

import server


class ParseSelectionTests(unittest.TestCase):
    def test_default_repeats(self):
        selection = server.parse_selection({"models": ["m1"], "mode": "warm"})
        self.assertEqual(selection["repeats"], 3)
        self.assertEqual(selection["context"], server.CONTEXT)
        self.assertEqual(selection["models"], ["m1"])
        self.assertEqual(selection["mode"], "warm")

    def test_accepts_repeats_bounds(self):
        self.assertEqual(
            server.parse_selection({"models": ["m1"], "mode": "warm", "repeats": 1})["repeats"], 1)
        self.assertEqual(
            server.parse_selection({"models": ["m1"], "mode": "warm", "repeats": 5})["repeats"], 5)

    def test_backwards_compatible_without_repeats(self):
        selection = server.parse_selection(
            {"models": ["a", "b"], "mode": "cold", "context": 4096})
        self.assertEqual(selection["repeats"], 3)
        self.assertEqual(selection["context"], 4096)
        self.assertEqual(selection["models"], ["a", "b"])

    def test_rejects_invalid_repeats(self):
        for bad in (0, 6, 1.5, "3", True, False, None):
            with self.assertRaises(ValueError):
                server.parse_selection({"models": ["m1"], "mode": "warm", "repeats": bad})

    def test_rejects_invalid_fields(self):
        cases = [
            {"models": [], "mode": "warm"},
            {"models": ["a", "b", "c"], "mode": "warm"},
            {"models": ["a", "a"], "mode": "warm"},
            {"models": [1], "mode": "warm"},
            {"models": [""], "mode": "warm"},
            {"models": ["a"], "mode": "hot"},
            {"models": ["a"], "mode": "warm", "context": 1000},
        ]
        for data in cases:
            with self.assertRaises(ValueError):
                server.parse_selection(data)


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self._save = server.save
        self._ollama_json = server.ollama_json
        self._upstream = server.upstream
        server.JOB.update(status="idle", model=None, error=None)
        self.saved = []
        self.final_packet = {
            "done": True,
            "done_reason": "stop",
            "load_duration": 500_000_000,
            "prompt_eval_count": 120,
            "prompt_eval_duration": 300_000_000,
            "eval_count": 300,
            "eval_duration": 6_000_000_000,
            "prompt_eval_cached_count": 0,
        }

    def tearDown(self):
        server.save = self._save
        server.ollama_json = self._ollama_json
        server.upstream = self._upstream
        server.JOB.update(status="idle", model=None, error=None)

    def _patch(self):
        final = self.final_packet
        server.save = lambda run, session, position: self.saved.append((run, session, position))

        def fake_ollama_json(path, data=None, timeout=5):
            if path == "/api/ps":
                return {"models": [
                    {"name": "m1", "size": 100, "size_vram": 100, "context_length": 8192},
                    {"name": "m2", "size": 100, "size_vram": 100, "context_length": 8192},
                ]}
            return {}

        class Response:
            def __enter__(self):
                return iter([json.dumps({"response": "x"}).encode(),
                             json.dumps(final).encode()])
            def __exit__(self, *exc):
                return False

        server.ollama_json = fake_ollama_json
        server.upstream = lambda path, data=None, timeout=5: Response()

    def test_repeats_per_model(self):
        self._patch()
        server.benchmark(["m1", "m2"], "warm", "session-1", 8192, repeats=3)
        self.assertEqual(len(self.saved), 6)
        self.assertEqual([run["model"] for run, _, _ in self.saved],
                         ["m1", "m1", "m1", "m2", "m2", "m2"])
        self.assertEqual([position for _, _, position in self.saved], [0, 1, 2, 3, 4, 5])
        self.assertEqual({session for _, session, _ in self.saved}, {"session-1"})

    def test_position_not_reset_between_models(self):
        self._patch()
        server.benchmark(["m1", "m2"], "warm", "session-4", 8192, repeats=2)
        self.assertEqual([p for _, _, p in self.saved], [0, 1, 2, 3])

    def test_single_run_default(self):
        self._patch()
        server.benchmark(["m1"], "warm", "session-2", 8192)
        self.assertEqual(len(self.saved), 1)
        self.assertEqual(self.saved[0][2], 0)

    def test_each_run_keeps_own_metrics_no_aggregation(self):
        self._patch()
        server.benchmark(["m1", "m2"], "warm", "session-3", 8192, repeats=2)
        self.assertEqual(len(self.saved), 4)
        for run, _, _ in self.saved:
            self.assertIsNotNone(run["decode"])
            self.assertIn("date", run)
            self.assertIn("first", run)
            self.assertIn("total", run)
            for key in ("median", "min", "max", "spread", "repeats", "mean"):
                self.assertNotIn(key, run)
        self.assertEqual(server.JOB["status"], "complete")


class ValidatePromptTests(unittest.TestCase):
    def test_accepts_a_normal_prompt(self):
        self.assertEqual(server.validate_prompt("hello"), "hello")

    def test_accepts_the_maximum_length(self):
        value = "x" * server.MAX_PROMPT_LENGTH
        self.assertEqual(server.validate_prompt(value), value)

    def test_rejects_empty_string(self):
        with self.assertRaises(ValueError):
            server.validate_prompt("")

    def test_rejects_whitespace_only(self):
        with self.assertRaises(ValueError):
            server.validate_prompt("   \n\t ")

    def test_rejects_non_string_int(self):
        with self.assertRaises(ValueError):
            server.validate_prompt(123)

    def test_rejects_non_string_list(self):
        with self.assertRaises(ValueError):
            server.validate_prompt(["a", "b"])

    def test_rejects_non_string_none(self):
        with self.assertRaises(ValueError):
            server.validate_prompt(None)

    def test_rejects_oversized_prompt(self):
        with self.assertRaises(ValueError):
            server.validate_prompt("x" * (server.MAX_PROMPT_LENGTH + 1))


class PromptApiTests(unittest.TestCase):
    """End-to-end tests against a real ThreadingHTTPServer on 127.0.0.1."""

    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(server.Handler, directory=str(server.ROOT)))
        cls.port = cls.httpd.server_port
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        # Reset the in-memory prompt and job state so tests stay independent.
        server.PROMPT = server.DEFAULT_PROMPT
        with server.LOCK:
            server.JOB.update(status="idle", model=None, error=None)

    def get(self, path):
        with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as response:
            return response.status, json.load(response)

    def post(self, path, payload):
        body = json.dumps(payload).encode()
        request = Request(f"http://127.0.0.1:{self.port}{path}", data=body, method="POST",
                          headers={"Content-Type": "application/json",
                                   "Origin": f"http://127.0.0.1:{self.port}"})
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, json.load(response)
        except Exception as error:  # HTTPError carries the status/body for 4xx.
            if hasattr(error, "code"):
                return error.code, json.loads(error.read().decode())
            raise

    def test_get_returns_default_prompt(self):
        status, payload = self.get("/api/prompt")
        self.assertEqual(status, 200)
        self.assertEqual(payload["prompt"], server.DEFAULT_PROMPT)
        self.assertEqual(payload["default"], server.DEFAULT_PROMPT)

    def test_post_persists_custom_prompt(self):
        custom = "Explain the CAP theorem in three bullet points."
        status, payload = self.post("/api/prompt", {"prompt": custom})
        self.assertEqual(status, 200)
        self.assertEqual(payload["prompt"], custom)
        self.assertEqual(server.PROMPT, custom)
        # A following GET reflects the persisted prompt.
        _, fetched = self.get("/api/prompt")
        self.assertEqual(fetched["prompt"], custom)
        self.assertEqual(fetched["default"], server.DEFAULT_PROMPT)

    def test_post_rejects_empty_prompt(self):
        status, _ = self.post("/api/prompt", {"prompt": ""})
        self.assertEqual(status, 400)

    def test_post_rejects_whitespace_prompt(self):
        status, _ = self.post("/api/prompt", {"prompt": "   "})
        self.assertEqual(status, 400)

    def test_post_rejects_non_string_prompt(self):
        status, _ = self.post("/api/prompt", {"prompt": {"nested": True}})
        self.assertEqual(status, 400)

    def test_post_rejects_oversized_prompt(self):
        status, _ = self.post("/api/prompt", {"prompt": "x" * (server.MAX_PROMPT_LENGTH + 1)})
        self.assertEqual(status, 400)

    def test_post_requires_origin(self):
        body = json.dumps({"prompt": "hi"}).encode()
        request = Request(f"http://127.0.0.1:{self.port}/api/prompt", data=body, method="POST",
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=5) as response:
                self.fail("expected 403")
        except Exception as error:
            self.assertEqual(getattr(error, "code", None), 403)

    def test_benchmarks_rejects_oversized_prompt_before_ollama(self):
        # Validated before any Ollama call, so no Ollama is needed.
        status, payload = self.post("/api/benchmarks", {
            "models": ["m"], "mode": "warm",
            "prompt": "x" * (server.MAX_PROMPT_LENGTH + 1),
        })
        self.assertEqual(status, 400)

    def test_benchmarks_passes_optional_prompt_to_benchmark(self):
        captured = []
        done = threading.Event()

        def fake_benchmark(models, mode, session, context, repeats=1, prompt=server.PROMPT):
            captured.append(prompt)
            with server.LOCK:
                server.JOB.update(status="complete", model=None)
            done.set()

        original_benchmark, original_installed = server.benchmark, server.installed_models
        server.benchmark, server.installed_models = fake_benchmark, lambda: ["m"]
        try:
            status, _ = self.post("/api/benchmarks", {"models": ["m"], "mode": "warm", "prompt": "custom prompt"})
            self.assertEqual(status, 202)
            self.assertTrue(done.wait(timeout=2), "benchmark thread did not run")
            self.assertEqual(captured, ["custom prompt"])
        finally:
            server.benchmark, server.installed_models = original_benchmark, original_installed

    def test_benchmarks_uses_current_prompt_when_omitted(self):
        captured = []
        done = threading.Event()

        def fake_benchmark(models, mode, session, context, repeats=1, prompt=server.PROMPT):
            captured.append(prompt)
            with server.LOCK:
                server.JOB.update(status="complete", model=None)
            done.set()

        original_benchmark, original_installed = server.benchmark, server.installed_models
        server.benchmark, server.installed_models = fake_benchmark, lambda: ["m"]
        try:
            # Set a session prompt, then omit `prompt` on the benchmark call.
            server.PROMPT = "session prompt"
            status, _ = self.post("/api/benchmarks", {"models": ["m"], "mode": "warm"})
            self.assertEqual(status, 202)
            self.assertTrue(done.wait(timeout=2), "benchmark thread did not run")
            self.assertEqual(captured, ["session prompt"])
        finally:
            server.benchmark, server.installed_models = original_benchmark, original_installed


if __name__ == "__main__":
    unittest.main()
