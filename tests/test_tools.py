import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forge.tools import ToolBox, ToolError  # noqa: E402


class ToolBoxTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="forge-test-")
        self.tb = ToolBox(self.root, test_timeout=60)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_write_read_roundtrip(self):
        ok, msg = self.tb.dispatch("write_file", {"path": "a.py", "content": "x = 1\n"})
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(os.path.join(self.root, "a.py")))
        ok, text = self.tb.dispatch("read_file", {"path": "a.py"})
        self.assertTrue(ok)
        self.assertEqual(text, "x = 1\n")

    def test_subdirectory_allowed(self):
        ok, _ = self.tb.dispatch(
            "write_file", {"path": "pkg/core.py", "content": "VALUE = 1\n"}
        )
        self.assertTrue(ok)
        ok, listing = self.tb.dispatch("list_files", {})
        self.assertTrue(ok)
        self.assertIn("pkg/core.py", listing)

    def test_path_traversal_rejected(self):
        for bad in ("../escape.py", "/etc/passwd", "a/../../b.py", ""):
            with self.assertRaises(ToolError, msg=bad):
                self.tb.dispatch("write_file", {"path": bad, "content": "x"})

    def test_deep_nesting_rejected(self):
        with self.assertRaises(ToolError):
            self.tb.dispatch(
                "write_file", {"path": "a/b/c.py", "content": "x"}
            )

    def test_binary_content_rejected(self):
        with self.assertRaises(ToolError):
            self.tb.dispatch("write_file", {"path": "b.bin", "content": "a\x00b"})

    def test_oversize_file_rejected(self):
        with self.assertRaises(ToolError):
            self.tb.dispatch(
                "write_file", {"path": "big.txt", "content": "x" * 200_001}
            )

    def test_missing_file(self):
        with self.assertRaises(ToolError):
            self.tb.dispatch("read_file", {"path": "nope.py"})

    def test_unknown_tool(self):
        with self.assertRaises(ToolError):
            self.tb.dispatch("rm_rf", {})

    def test_bad_json_arguments_are_object(self):
        with self.assertRaises(ToolError):
            self.tb.dispatch("write_file", {"path": 3, "content": "x"})

    def test_zero_discovered_tests_is_not_green(self):
        ok, obs = self.tb.dispatch("run_tests", {})
        self.assertFalse(ok, "empty sandbox must not count as passing tests")
        self.assertIn("no test files", obs)
        self.assertFalse(self.tb.tests_green)

    def test_failing_then_passing_tests(self):
        self.tb.dispatch(
            "write_file",
            {
                "path": "subject.py",
                "content": "def add(a, b):\n    return a - b\n",
            },
        )
        self.tb.dispatch(
            "write_file",
            {
                "path": "test_subject.py",
                "content": "import unittest\nimport subject\n\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_add(self):\n"
                "        self.assertEqual(subject.add(2, 3), 5)\n",
            },
        )
        ok, obs = self.tb.dispatch("run_tests", {})
        self.assertFalse(ok)
        self.assertIn("exit_code: 1", obs)
        self.tb.dispatch(
            "write_file", {"path": "subject.py", "content": "def add(a, b):\n    return a + b\n"}
        )
        ok, obs = self.tb.dispatch("run_tests", {})
        self.assertTrue(ok, obs)
        self.assertIn("OK", obs)
        self.assertTrue(self.tb.tests_green)

    def test_finish_requires_summary(self):
        with self.assertRaises(ToolError):
            self.tb.dispatch("finish", {"summary": "  "})
        ok, _ = self.tb.dispatch("finish", {"summary": "done"})
        self.assertTrue(ok)
        self.assertTrue(self.tb.finished)
        self.assertEqual(self.tb.summary, "done")

    def test_env_is_scrubbed_for_test_subprocess(self):
        self.tb.dispatch(
            "write_file",
            {
                "path": "test_env.py",
                "content": "import os\nimport unittest\n\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_no_key(self):\n"
                "        self.assertNotIn('NEBIUS_API_KEY', os.environ)\n",
            },
        )
        ok, obs = self.tb.dispatch("run_tests", {})
        self.assertTrue(ok, obs)


if __name__ == "__main__":
    unittest.main()
