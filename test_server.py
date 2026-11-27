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
        self._sandbox = server.run_tests_sandboxed
        server.JOB.update(status="idle", model=None, error=None)
        self.saved = []
        self.sandbox_calls = []
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
        server.run_tests_sandboxed = self._sandbox
        server.JOB.update(status="idle", model=None, error=None)

    def _patch(self):
        final = self.final_packet
        server.save = lambda run, session, position: self.saved.append((run, session, position))
        server.run_tests_sandboxed = lambda code, timeout=server.SANDBOX_TIMEOUT: (
            self.sandbox_calls.append(code) or {"correct": True, "passed": 4, "total": 4, "quality_error": None})

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


class SandboxTests(unittest.TestCase):
    """The sandbox runner executes generated unittest cases in an isolated subprocess."""

    PASSING = '''
import unittest


def merge(intervals):
    if not intervals:
        return []
    out = []
    for start, end in sorted(intervals):
        if out and start <= out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return out


class TestMerge(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(merge([]), [])

    def test_unsorted(self):
        self.assertEqual(merge([[5, 7], [1, 3]]), [[1, 3], [5, 7]])

    def test_touching(self):
        self.assertEqual(merge([[1, 2], [2, 3]]), [[1, 3]])

    def test_separate(self):
        self.assertEqual(merge([[1, 2], [4, 5]]), [[1, 2], [4, 5]])
'''

    FAILING = '''
import unittest


def merge(intervals):
    return []


class TestMerge(unittest.TestCase):
    def test_non_empty(self):
        self.assertEqual(merge([[1, 2]]), [[1, 2]])

    def test_empty(self):
        self.assertEqual(merge([]), [])
'''

    def test_passing_sample(self):
        result = server.run_tests_sandboxed(self.PASSING)
        self.assertTrue(result["correct"])
        self.assertEqual(result["passed"], 4)
        self.assertEqual(result["total"], 4)
        self.assertIsNone(result["quality_error"])

    def test_deliberately_failing_sample(self):
        result = server.run_tests_sandboxed(self.FAILING)
        self.assertFalse(result["correct"])
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["passed"], 1)
        self.assertIsNone(result["quality_error"])

    def test_non_code_sample(self):
        result = server.run_tests_sandboxed("x = 42")
        self.assertIsNone(result["correct"])
        self.assertEqual(result["quality_error"], "no_tests")

    def test_prose_refusal_reported_as_no_tests(self):
        result = server.run_tests_sandboxed("Sorry, I cannot generate that.")
        self.assertIsNone(result["correct"])
        self.assertEqual(result["quality_error"], "no_tests")

    def test_syntax_error_sample(self):
        result = server.run_tests_sandboxed("def broken(:")
        self.assertIsNone(result["correct"])
        self.assertEqual(result["quality_error"], "syntax")

    def test_timeout_sample(self):
        code = ("import unittest\n"
                "class T(unittest.TestCase):\n"
                "    def test_a(self):\n"
                "        while True:\n"
                "            pass\n")
        result = server.run_tests_sandboxed(code, timeout=1)
        self.assertIsNone(result["correct"])
        self.assertEqual(result["quality_error"], "timeout")

    def test_never_crashes_on_garbage(self):
        for sample in ("", "   ", "\x00\x01\x02", "\ud800"):
            result = server.run_tests_sandboxed(sample)
            self.assertIn("quality_error", result)
            self.assertIsNone(result["correct"])


class CorrectnessPersistenceTests(unittest.TestCase):
    """The benchmark stores the correctness result and never the generated text."""

    def setUp(self):
        self._sandbox = server.run_tests_sandboxed
        self._save = server.save
        self._ollama_json = server.ollama_json
        self._upstream = server.upstream
        server.JOB.update(status="idle", model=None, error=None)
        self.saved = []

    def tearDown(self):
        server.run_tests_sandboxed = self._sandbox
        server.save = self._save
        server.ollama_json = self._ollama_json
        server.upstream = self._upstream
        server.JOB.update(status="idle", model=None, error=None)

    def _run_with(self, text):
        server.save = lambda run, session, position: self.saved.append(run)
        server.run_tests_sandboxed = lambda code, timeout=server.SANDBOX_TIMEOUT: (
            {"correct": True, "passed": 4, "total": 4, "quality_error": None})

        def fake_ollama_json(path, data=None, timeout=5):
            return {"models": []} if path == "/api/ps" else {}

        class Response:
            def __enter__(self):
                return iter([json.dumps({"response": text}).encode(),
                             json.dumps({"done": True, "done_reason": "stop",
                                         "eval_count": 10, "eval_duration": 1_000_000_000,
                                         "prompt_eval_count": 1, "prompt_eval_duration": 1_000_000_000}).encode()])
            def __exit__(self, *exc):
                return False

        server.ollama_json = fake_ollama_json
        server.upstream = lambda path, data=None, timeout=5: Response()
        server.benchmark(["m1"], "warm", "sess", 8192, repeats=1, prompt=server.DEFAULT_PROMPT)

    def test_correctness_fields_persisted(self):
        self._run_with("def merge(x): return x")
        run = self.saved[0]
        self.assertIn("quality", run)
        quality = run["quality"]
        self.assertIn("correct", quality)
        self.assertIn("passed", quality)
        self.assertIn("total", quality)
        self.assertIn("quality_error", quality)
        self.assertIs(quality["correct"], True)
        self.assertEqual(quality["passed"], 4)
        self.assertEqual(quality["total"], 4)

    def test_generated_text_is_not_persisted(self):
        self._run_with("SECRET-GENERATED-TEXT-12345")
        run = self.saved[0]
        blob = json.dumps(run)
        self.assertNotIn("SECRET-GENERATED-TEXT-12345", blob)
        for key in ("response", "text", "code", "prompt_text"):
            self.assertNotIn(key, run)


if __name__ == "__main__":
    unittest.main()
