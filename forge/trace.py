"""Console trace + JSONL transcript for a Forge run."""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Optional

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RESET = "\033[0m"


class Trace:
    def __init__(self, stream=None, color: bool = True, jsonl_path: Optional[str] = None):
        self.stream = stream or sys.stdout
        self.color = color and hasattr(self.stream, "isatty") and self.stream.isatty()
        self.jsonl_path = jsonl_path
        self._jsonl = None
        if jsonl_path:
            parent = os.path.dirname(os.path.abspath(jsonl_path))
            os.makedirs(parent, exist_ok=True)
            self._jsonl = open(jsonl_path, "w", encoding="utf-8")

    # ------------------------------------------------------------------ utils
    def _c(self, code: str, text: str) -> str:
        if not self.color:
            return text
        return code + text + RESET

    def _w(self, text: str = "") -> None:
        self.stream.write(text + "\n")
        self.stream.flush()

    def event(self, kind: str, **fields: Any) -> None:
        if self._jsonl:
            rec = {"event": kind}
            rec.update(fields)
            self._jsonl.write(json.dumps(rec, sort_keys=True) + "\n")
            self._jsonl.flush()

    # ------------------------------------------------------------------ views
    def header(self, cfg, out_dir: str) -> None:
        bar = "=" * 74
        self._w(self._c(BOLD, bar))
        self._w(self._c(BOLD, " FORGE  -  natural language goal -> runnable, tested repo"))
        backend = "mock (offline, scripted)" if not cfg.is_real else "Nebius Token Factory"
        model = cfg.model if cfg.is_real else "scripted-demo"
        self._w(" backend : %s" % backend)
        self._w(" model   : %s" % model)
        if cfg.is_real:
            self._w(" base_url: %s" % cfg.base_url)
        self._w(" goal    : %s" % cfg.goal)
        self._w(" sandbox : %s" % out_dir)
        self._w(self._c(BOLD, bar))

    def step(self, index: int, total: int, narration: str) -> None:
        head = "[%d/%d]" % (index, total)
        self._w("")
        self._w(self._c(CYAN, head) + " " + (narration or self._c(DIM, "(no narration)")))
        self.event("step", index=index, narration=narration)

    def call(self, name: str, args: Dict[str, Any]) -> None:
        self._w("        " + self._c(YELLOW, "-> " + name) + self._c(DIM, "(" + _fmt_args(name, args) + ")"))
        self.event("tool_call", name=name, args=args)

    def observation(self, name: str, ok: bool, text: str) -> None:
        mark = self._c(GREEN, "  ok  ") if ok else self._c(RED, " fail ")
        lines = text.splitlines() or [""]
        self._w("        %s %s" % (mark, lines[0]))
        # Test runs always show their captured output; other tools only on error.
        if not ok or name == "run_tests":
            code = GREEN if ok else DIM
            for line in lines[1:]:
                self._w("        " + self._c(code, line))
        self.event("tool_result", name=name, ok=ok, text=text)

    def finish(self, result) -> None:
        self._w("")
        if result.ok:
            self._w(
                self._c(GREEN, " PASS ")
                + " %d steps, %d file(s), %d test run(s), tests green"
                % (result.steps, len(result.files), result.test_runs)
            )
        elif result.finished:
            self._w(self._c(YELLOW, " DONE ") + " finished, but tests were not green")
        else:
            self._w(
                self._c(RED, " INCOMPLETE ")
                + " stopped after %d steps without finish()" % result.steps
            )
        self._w("")
        self._w(self._c(BOLD, " summary:"))
        summary = result.summary or "(none)"
        for line in _wrap(summary, 72):
            self._w("   " + line)
        self._w("")
        self._w(" files in %s:" % result.out_dir)
        for f in result.files:
            self._w("   - " + f)
        self.event(
            "run_complete",
            ok=result.ok,
            finished=result.finished,
            steps=result.steps,
            files=result.files,
            tests_green=result.tests_green,
        )

    def error(self, message: str) -> None:
        self._w(self._c(RED, "ERROR: ") + message)
        self.event("error", message=message)

    def close(self) -> None:
        if self._jsonl:
            self._jsonl.close()
            self._jsonl = None


def _fmt_args(name: str, args: Dict[str, Any]) -> str:
    if not args:
        return ""
    if name == "write_file":
        content = str(args.get("content", ""))
        return "%s, %d chars" % (args.get("path"), len(content))
    if name == "read_file":
        return str(args.get("path"))
    out = ", ".join("%s=%s" % (k, _short(v)) for k, v in args.items())
    return out


def _short(value: Any, limit: int = 60) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _wrap(text: str, width: int):
    words = text.split()
    line: list = []
    for word in words:
        if sum(len(w) + 1 for w in line) + len(word) > width and line:
            yield " ".join(line)
            line = [word]
        else:
            line.append(word)
    if line:
        yield " ".join(line)
