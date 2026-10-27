import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forge.agent import run_agent  # noqa: E402
from forge.llm import MockBackend, assistant_message  # noqa: E402
from forge.config import Config  # noqa: E402
from forge.trace import Trace  # noqa: E402


def cfg(goal, out_dir, **kw):
    params = dict(goal=goal, mode="mock", out_dir=out_dir, max_steps=12)
    params.update(kw)
    return Config(**params)


class AgentLoopTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="forge-agent-")
        self.trace = Trace(stream=io.StringIO(), color=False)

    def tearDown(self):
        self.trace.close()
        shutil.rmtree(self.root, ignore_errors=True)

    def test_mock_loop_builds_and_tests_project(self):
        c = cfg("demo goal", self.root)
        result = run_agent(c, MockBackend(c), self.trace)
        self.assertTrue(result.ok, "mock run should end with passing tests")
        self.assertTrue(result.finished)
        self.assertEqual(result.steps, 8)
        self.assertEqual(result.test_runs, 2)
        self.assertIn("tempconv.py", result.files)
        self.assertIn("test_tempconv.py", result.files)
        self.assertIn("README.md", result.files)
        self.assertIn("tempconv", result.summary)

    def test_trace_records_events(self):
        path = os.path.join(self.root, "..", "trace-%d.jsonl" % os.getpid())
        trace = Trace(stream=io.StringIO(), color=False, jsonl_path=path)
        try:
            c = cfg("demo goal", os.path.join(self.root, "b"))
            run_agent(c, MockBackend(c), trace)
        finally:
            trace.close()
        try:
            with open(path) as fh:
                events = [json.loads(line) for line in fh if line.strip()]
            kinds = [e["event"] for e in events]
            self.assertIn("run_complete", kinds)
            self.assertEqual(kinds.count("tool_call"), 8)
            final = [e for e in events if e["event"] == "run_complete"][0]
            self.assertTrue(final["ok"])
        finally:
            os.unlink(path)

    def test_finish_rejected_until_tests_pass(self):
        class FinishOnly:
            name = "fake"
            label = "fake"

            def __init__(self):
                self.n = 0

            def complete(self, messages, tools):
                self.n += 1
                return assistant_message(
                    "Done!",
                    [
                        {
                            "id": "c%d" % self.n,
                            "type": "function",
                            "function": {"name": "finish", "arguments": '{"summary": "done"}'},
                        }
                    ],
                )

        c = cfg("x", os.path.join(self.root, "fin"), max_steps=3)
        result = run_agent(c, FinishOnly(), self.trace)
        self.assertFalse(result.ok, "finish without green tests must not be a pass")

    def test_backend_error_is_reported_not_raised(self):
        class Boom:
            name = "boom"
            label = "boom"

            def complete(self, messages, tools):
                raise RuntimeError("endpoint unreachable")

        c = cfg("x", os.path.join(self.root, "boom"))
        result = run_agent(c, Boom(), self.trace)
        self.assertFalse(result.ok)
        self.assertFalse(result.finished)
        self.assertIn("endpoint unreachable", result.error)

    def test_no_tool_calls_terminates(self):
        class Chatty:
            name = "chatty"
            label = "chatty"

            def complete(self, messages, tools):
                return assistant_message("I have no tools to call.", [])

        c = cfg("x", os.path.join(self.root, "chatty"), max_steps=6)
        result = run_agent(c, Chatty(), self.trace)
        self.assertFalse(result.finished)
        self.assertLessEqual(result.steps, 3)

    def test_bad_tool_arguments_are_observed(self):
        class BadArgs:
            name = "bad"
            label = "bad"

            def __init__(self):
                self.n = 0

            def complete(self, messages, tools):
                self.n += 1
                if self.n == 1:
                    return assistant_message(
                        "trying",
                        [
                            {
                                "id": "c1",
                                "type": "function",
                                "function": {"name": "write_file", "arguments": "{not json"},
                            }
                        ],
                    )
                return assistant_message("stop", [])

        c = cfg("x", os.path.join(self.root, "bad"), max_steps=4)
        result = run_agent(c, BadArgs(), self.trace)
        self.assertFalse(result.ok)
        out = self.trace.stream.getvalue()
        self.assertIn("not valid JSON", out)


if __name__ == "__main__":
    unittest.main()
