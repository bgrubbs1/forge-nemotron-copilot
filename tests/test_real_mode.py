"""End-to-end tests of REAL mode's HTTP path against a local fake endpoint.

These tests prove that when a Nebius API key is present, Forge sends
OpenAI-compatible ``tools`` requests, carries ``tool_calls`` and ``role: tool``
messages through the loop, and finishes green - on a machine with no key.
"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from fake_nebius_server import EXPECTED_KEY, FakeNebiusServer  # noqa: E402
from forge.agent import run_agent  # noqa: E402
from forge.llm import BackendError, NebiusBackend, make_backend  # noqa: E402
from forge.trace import Trace  # noqa: E402


class RealModeHttpTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="forge-real-")
        self.server = FakeNebiusServer()
        self.server.__enter__()
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.addCleanup(lambda: self.server.__exit__(None, None, None))

    def test_full_agent_run_over_http(self):
        cfg = self.server.config(out_dir=os.path.join(self.tmp, "build"))
        backend = make_backend(cfg)
        self.assertIsInstance(backend, NebiusBackend)
        trace = Trace(stream=io.StringIO(), color=False)
        try:
            result = run_agent(cfg, backend, trace)
        finally:
            trace.close()
        self.assertTrue(result.ok, "real-mode HTTP run should end green")
        self.assertTrue(result.finished)
        self.assertEqual(result.test_runs, 2)
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "build", "tempconv.py")))
        self.assertEqual(len(self.server.requests), 8, "one HTTP call per step")

    def test_wire_format_is_openai_compatible(self):
        cfg = self.server.config(out_dir=os.path.join(self.tmp, "w"))
        trace = Trace(stream=io.StringIO(), color=False)
        try:
            run_agent(cfg, make_backend(cfg), trace)
        finally:
            trace.close()

        first = self.server.requests[0]
        self.assertEqual(first["model"], cfg.model)
        self.assertEqual(first["tool_choice"], "auto")
        self.assertEqual(first["temperature"], 0.2)
        self.assertEqual(
            {t["function"]["name"] for t in first["tools"]},
            {"write_file", "read_file", "list_files", "run_tests", "finish"},
        )
        self.assertEqual(first["messages"][0]["role"], "system")
        self.assertEqual(first["messages"][1]["role"], "user")

        # after the first turn the conversation must contain an assistant
        # tool_calls turn followed by a role=tool message
        second = self.server.requests[1]["messages"]
        self.assertEqual([m["role"] for m in second][:3], ["system", "user", "assistant"])
        self.assertTrue(second[2].get("tool_calls"))
        self.assertEqual(second[3]["role"], "tool")
        self.assertEqual(second[3]["tool_call_id"], second[2]["tool_calls"][0]["id"])
        self.assertIn("wrote SPEC.md", second[3]["content"])

    def test_bearer_auth_is_sent(self):
        cfg = self.server.config(out_dir=os.path.join(self.tmp, "a"))
        trace = Trace(stream=io.StringIO(), color=False)
        try:
            run_agent(cfg, make_backend(cfg), trace)
        finally:
            trace.close()
        self.assertIn("Bearer %s" % EXPECTED_KEY, self.server.seen_auth)

    def test_wrong_key_gives_actionable_error(self):
        cfg = self.server.config(api_key="wrong-key", out_dir=os.path.join(self.tmp, "bad"))
        backend = NebiusBackend(cfg)
        with self.assertRaises(BackendError) as ctx:
            backend.complete([{"role": "user", "content": "hi"}], [])
        self.assertIn("authentication failed", str(ctx.exception))
        self.assertIn("NEBIUS_API_KEY", str(ctx.exception))

    def test_list_models_hits_endpoint(self):
        cfg = self.server.config(out_dir=os.path.join(self.tmp, "m"))
        ids = NebiusBackend(cfg).list_models()
        self.assertIn(cfg.model, ids)
        self.assertEqual(self.server.model_lists, 1)

    def test_404_on_bad_model_mentions_models_flag(self):
        cfg = self.server.config(
            out_dir=os.path.join(self.tmp, "404"),
            base_url=self.server.base_url + "/nope",
        )
        with self.assertRaises(BackendError) as ctx:
            NebiusBackend(cfg).complete([{"role": "user", "content": "hi"}], [])
        self.assertIn("404", str(ctx.exception))
        self.assertIn("--models", str(ctx.exception))

    def test_connection_refused_is_reported(self):
        cfg = self.server.config(
            out_dir=os.path.join(self.tmp, "refused"),
            base_url="http://127.0.0.1:9/v1",  # discard port, nothing listens
        )
        backend = NebiusBackend(cfg, max_retries=0)
        with self.assertRaises(BackendError):
            backend.complete([{"role": "user", "content": "hi"}], [])


if __name__ == "__main__":
    unittest.main()
