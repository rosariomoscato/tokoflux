"""Tests for the Tokoflux server (stdlib unittest, no external dependencies)."""
import json
import unittest

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


if __name__ == "__main__":
    unittest.main()
