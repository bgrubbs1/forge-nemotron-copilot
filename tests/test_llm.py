import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forge import demo_assets  # noqa: E402
from forge.llm import (  # noqa: E402
    BackendError,
    MockBackend,
    NebiusBackend,
    _parse_text_tool_calls,
)
from forge.config import Config  # noqa: E402


def mock_cfg(**kw):
    params = dict(goal="demo", mode="mock", out_dir="build")
    params.update(kw)
    return Config(**params)


def real_cfg(**kw):
    params = dict(
        goal="demo",
        mode="real",
        api_key="test-key-not-real",
        base_url="https://example.invalid/v1",
        model="nvidia/nemotron-test",
    )
    params.update(kw)
    return Config(**params)


class MockBackendTest(unittest.TestCase):
    def test_script_ends_with_finish_and_is_deterministic(self):
        a, b = MockBackend(mock_cfg()), MockBackend(mock_cfg())
        seq_a = [a.complete([], [])["tool_calls"][0]["function"]["name"] for _ in range(8)]
        seq_b = [b.complete([], [])["tool_calls"][0]["function"]["name"] for _ in range(8)]
        self.assertEqual(seq_a, seq_b)
        self.assertEqual(seq_a[-1], "finish")
        self.assertEqual(seq_a.count("run_tests"), 2)
        self.assertEqual(seq_a.count("write_file"), 5)

    def test_script_is_exhausted_gracefully(self):
        backend = MockBackend(mock_cfg())
        for _ in range(8):
            backend.complete([], [])
        msg = backend.complete([], [])
        self.assertEqual(msg.get("tool_calls", []), [])

    def test_demo_assets_differ_only_in_offset(self):
        self.assertIn("KELVIN_OFFSET = 273  # BUG", demo_assets.TEMPconv_V1)
        self.assertIn("KELVIN_OFFSET = 273.15", demo_assets.TEMPconv_V2)
        self.assertNotIn("KELVIN_OFFSET = 273.15", demo_assets.TEMPconv_V1)


class TextToolCallParsingTest(unittest.TestCase):
    def test_fenced_json(self):
        text = 'I will write it.\n```json\n{"tool": "write_file", "arguments": {"path": "a.py", "content": "x"}}\n```'
        calls = _parse_text_tool_calls(text)
        self.assertEqual(len(calls), 1)
        fn = calls[0]["function"]
        self.assertEqual(fn["name"], "write_file")
        self.assertEqual(json.loads(fn["arguments"])["path"], "a.py")

    def test_bare_json(self):
        calls = _parse_text_tool_calls('{"name": "run_tests", "parameters": {}}')
        self.assertEqual(calls[0]["function"]["name"], "run_tests")

    def test_unknown_tool_ignored(self):
        self.assertEqual(_parse_text_tool_calls('{"tool": "shell", "arguments": {}}'), [])

    def test_plain_prose_ignored(self):
        self.assertEqual(_parse_text_tool_calls("Just thinking out loud."), [])


class FakeNebius(NebiusBackend):
    def __init__(self, response):
        self.cfg = real_cfg()
        self.max_retries = 0
        self.label = "fake"
        self._response = response

    def _request(self, method, path, payload=None):
        self.last_payload = payload
        return self._response


class NebiusBackendTest(unittest.TestCase):
    def test_native_tool_calls_normalised(self):
        backend = FakeNebius(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Writing the file.",
                            "tool_calls": [
                                {
                                    "id": "call_abc",
                                    "type": "function",
                                    "function": {
                                        "name": "write_file",
                                        "arguments": '{"path": "a.py", "content": "x = 1"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        )
        msg = backend.complete([{"role": "user", "content": "hi"}], [])
        self.assertEqual(msg["content"], "Writing the file.")
        self.assertEqual(msg["tool_calls"][0]["id"], "call_abc")
        self.assertEqual(msg["tool_calls"][0]["function"]["name"], "write_file")
        # request shape is OpenAI-compatible
        self.assertEqual(backend.last_payload["tool_choice"], "auto")
        self.assertEqual(backend.last_payload["model"], "nvidia/nemotron-test")
        self.assertIn("tools", backend.last_payload)

    def test_dict_arguments_accepted(self):
        backend = FakeNebius(
            {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "c1",
                                    "function": {
                                        "name": "run_tests",
                                        "arguments": {"_": 1},
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        )
        msg = backend.complete([], [])
        self.assertEqual(json.loads(msg["tool_calls"][0]["function"]["arguments"]), {"_": 1})

    def test_text_fallback_and_list_content(self):
        backend = FakeNebius(
            {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": '{"tool": "run_tests", "arguments": {}}',
                                }
                            ]
                        }
                    }
                ]
            }
        )
        msg = backend.complete([], [])
        self.assertEqual(msg["tool_calls"][0]["function"]["name"], "run_tests")
        self.assertEqual(msg["content"], "")  # tool JSON stripped from narration

    def test_malformed_response_raises(self):
        backend = FakeNebius({"unexpected": True})
        with self.assertRaises(BackendError):
            backend.complete([], [])

    def test_list_models(self):
        backend = FakeNebius(
            {"data": [{"id": "nvidia/nemotron-3-super-120b-a12b"}, {"id": "other/model"}]}
        )
        ids = backend.list_models()
        self.assertEqual(ids, ["nvidia/nemotron-3-super-120b-a12b", "other/model"])


if __name__ == "__main__":
    unittest.main()
