"""Sandboxed tools the agent is allowed to call.

Safety model (small but real):
  * every path is resolved with ``realpath`` and must live under the sandbox
    root; absolute paths, ``..`` and symlink escapes are rejected
  * only UTF-8 text files are written, capped at 200 KB
  * the only process ever spawned is ``python -m unittest discover`` inside the
    sandbox, with a timeout and captured output
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

MAX_FILE_BYTES = 200_000
MAX_OBSERVATION_CHARS = 6_000
MAX_FILES = 40


class ToolError(Exception):
    """A tool call was invalid (bad path, unknown tool, ...)."""


def _truncate(text: str, limit: int = MAX_OBSERVATION_CHARS) -> str:
    if len(text) <= limit:
        return text
    head = text[: limit // 3]
    tail = text[-(limit - len(head)) :]
    return head + "\n... [truncated] ...\n" + tail


class ToolBox:
    """Executes tool calls against ``root`` and records run state."""

    def __init__(self, root: str, test_timeout: int = 120):
        self.root = os.path.realpath(root)
        os.makedirs(self.root, exist_ok=True)
        self.test_timeout = test_timeout
        self.finished = False
        self.summary: Optional[str] = None
        self.tests_green = False
        self.test_runs = 0
        self.writes: List[str] = []

    # ------------------------------------------------------------------ paths
    def _resolve(self, rel: str) -> str:
        if not isinstance(rel, str) or not rel.strip():
            raise ToolError("path must be a non-empty string")
        rel = rel.strip().replace("\\", "/")
        if os.path.isabs(rel) or rel.startswith("/"):
            raise ToolError("absolute paths are not allowed; use a relative path")
        parts = [p for p in rel.split("/") if p not in ("", ".")]
        if not parts:
            raise ToolError("path resolves to the sandbox root")
        if any(p == ".." for p in parts):
            raise ToolError("'..' is not allowed in paths")
        target = os.path.realpath(os.path.join(self.root, *parts))
        if target != self.root and not target.startswith(self.root + os.sep):
            raise ToolError("path escapes the sandbox: %s" % rel)
        if len(parts) > 2:
            raise ToolError("keep the project flat: at most one subdirectory")
        return target

    def _rel(self, abs_path: str) -> str:
        return os.path.relpath(abs_path, self.root).replace(os.sep, "/")

    # ------------------------------------------------------------------ tools
    def write_file(self, path: str, content: str) -> Tuple[bool, str]:
        target = self._resolve(path)
        if not isinstance(content, str):
            raise ToolError("content must be a string")
        if "\x00" in content:
            raise ToolError("refusing to write binary content (NUL byte found)")
        data = content.encode("utf-8")
        if len(data) > MAX_FILE_BYTES:
            raise ToolError(
                "file too large (%d bytes > %d)" % (len(data), MAX_FILE_BYTES)
            )
        if len(self.writes) >= MAX_FILES:
            raise ToolError("too many files written (%d); finish the project" % MAX_FILES)
        os.makedirs(os.path.dirname(target) or self.root, exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        rel = self._rel(target)
        self.writes.append(rel)
        return True, "wrote %s (%d bytes)" % (rel, len(data))

    def read_file(self, path: str) -> Tuple[bool, str]:
        target = self._resolve(path)
        if not os.path.isfile(target):
            raise ToolError("no such file: %s" % path)
        with open(target, "r", encoding="utf-8", errors="replace") as fh:
            return True, _truncate(fh.read())

    def list_files(self) -> Tuple[bool, str]:
        rows: List[str] = []
        for dirpath, _dirnames, filenames in os.walk(self.root):
            for name in sorted(filenames):
                full = os.path.join(dirpath, name)
                rows.append("%8d  %s" % (os.path.getsize(full), self._rel(full)))
        if not rows:
            return True, "(sandbox is empty)"
        return True, "\n".join(sorted(rows))

    def run_tests(self) -> Tuple[bool, str]:
        cmd = [sys.executable, "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py", "-v"]
        self.test_runs += 1
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=self.test_timeout,
                env=self._clean_env(),
            )
        except subprocess.TimeoutExpired:
            self.tests_green = False
            return False, "tests timed out after %ss" % self.test_timeout
        out = proc.stdout.decode("utf-8", errors="replace")
        self.tests_green = proc.returncode == 0
        body = _truncate(out)
        if not out.strip():
            body = "(no output)"
        if self.tests_green and "Ran 0 tests" in out:
            # `unittest discover` exits 0 when it finds nothing; that is not a pass.
            self.tests_green = False
            body = "no test files were discovered (test_*.py). Write tests first.\n" + body
        status = self.tests_green
        return status, "exit_code: %d\n--- output ---\n%s" % (proc.returncode, body)

    def finish(self, summary: str) -> Tuple[bool, str]:
        if not isinstance(summary, str) or not summary.strip():
            raise ToolError("finish needs a non-empty summary")
        self.finished = True
        self.summary = summary.strip()
        return True, "run finished"

    # ------------------------------------------------------------------ plumbing
    @staticmethod
    def _clean_env() -> Dict[str, str]:
        """Subprocess env without API keys or other ambient secrets."""
        env = {
            k: v
            for k, v in os.environ.items()
            if k in ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "SYSTEMROOT")
        }
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return env

    TOOL_METHODS = ("write_file", "read_file", "list_files", "run_tests", "finish")

    def dispatch(self, name: str, args: dict) -> Tuple[bool, str]:
        """Run one tool call. Returns ``(ok, observation_text)``."""
        if name not in self.TOOL_METHODS:
            raise ToolError("unknown tool: %s" % name)
        if args is None:
            args = {}
        if not isinstance(args, dict):
            raise ToolError("tool arguments must be a JSON object")
        method = getattr(self, name)
        if name in ("list_files", "run_tests"):
            return method()
        if name == "finish":
            return method(str(args.get("summary", "")))
        return method(**args)

    # ------------------------------------------------------------------ result
    def snapshot(self) -> Dict[str, object]:
        files = []
        for dirpath, _d, filenames in os.walk(self.root):
            for fname in filenames:
                files.append(self._rel(os.path.join(dirpath, fname)))
        return {
            "files": sorted(files),
            "tests_green": self.tests_green,
            "test_runs": self.test_runs,
            "finished": self.finished,
            "summary": self.summary,
            "root": self.root,
        }
