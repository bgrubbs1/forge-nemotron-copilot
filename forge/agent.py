"""The agent loop: model -> tool calls -> observations -> repeat."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .config import Config
from .prompt import SYSTEM_PROMPT, TOOL_SCHEMAS, user_prompt
from .tools import ToolBox, ToolError

MAX_CONSECUTIVE_NO_TOOL_TURNS = 2
MAX_FINISH_REJECTIONS = 2


@dataclass
class RunResult:
    ok: bool
    finished: bool
    steps: int
    summary: Optional[str]
    out_dir: str
    files: List[str] = field(default_factory=list)
    tests_green: bool = False
    test_runs: int = 0
    backend: str = ""
    error: Optional[str] = None


def _parse_args(raw: Any) -> Dict[str, Any]:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise ToolError("tool arguments were not valid JSON: %s" % exc)
    if not isinstance(parsed, dict):
        raise ToolError("tool arguments must be a JSON object")
    return parsed


def run_agent(cfg: Config, backend, trace) -> RunResult:
    """Run the tool-call loop to completion (or the step budget)."""
    out_dir = os.path.realpath(cfg.out_dir)
    toolbox = ToolBox(out_dir, test_timeout=cfg.timeout)
    trace.header(cfg, out_dir)

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt(cfg.goal)},
    ]

    consecutive_no_tool = 0
    finish_rejections = 0
    steps = 0
    error: Optional[str] = None

    while steps < cfg.max_steps:
        steps += 1
        try:
            message = backend.complete(messages, TOOL_SCHEMAS)
        except Exception as exc:  # backend failure ends the run cleanly
            error = "%s: %s" % (type(exc).__name__, exc)
            trace.error(error)
            break

        content = (message.get("content") or "").strip()
        calls = message.get("tool_calls") or []
        trace.step(steps, cfg.max_steps, content)

        # Record the assistant turn exactly as received (required for the next
        # request in OpenAI-compatible tool-calling flows).
        assistant_turn: Dict[str, Any] = {"role": "assistant", "content": content}
        if calls:
            assistant_turn["tool_calls"] = calls
        messages.append(assistant_turn)

        if not calls:
            consecutive_no_tool += 1
            if consecutive_no_tool >= MAX_CONSECUTIVE_NO_TOOL_TURNS:
                trace.error("model stopped calling tools; ending run")
                break
            messages.append(
                {
                    "role": "user",
                    "content": "Continue. Call one of the tools (write_file, read_file, "
                    "list_files, run_tests) and call finish only when tests pass.",
                }
            )
            continue
        consecutive_no_tool = 0

        for call in calls:
            fn = call.get("function") or {}
            name = fn.get("name") or ""
            call_id = call.get("id") or "call_%d" % steps
            try:
                args = _parse_args(fn.get("arguments"))
            except ToolError as exc:
                trace.call(name or "?", {})
                trace.observation(name or "?", False, "ERROR: %s" % exc)
                messages.append(
                    {"role": "tool", "tool_call_id": call_id, "name": name, "content": "ERROR: %s" % exc}
                )
                continue

            trace.call(name, args)

            if name == "finish" and not toolbox.tests_green:
                finish_rejections += 1
                if finish_rejections <= MAX_FINISH_REJECTIONS:
                    obs = (
                        "ERROR: not finishing - the test suite has not passed yet. "
                        "Fix the code, run_tests until exit code 0, then call finish."
                    )
                    trace.observation(name, False, obs)
                    messages.append(
                        {"role": "tool", "tool_call_id": call_id, "name": name, "content": obs}
                    )
                    continue

            try:
                ok, observation = toolbox.dispatch(name, args)
            except ToolError as exc:
                ok, observation = False, "ERROR: %s" % exc
            except Exception as exc:  # never let a tool crash the run
                ok, observation = False, "ERROR: tool crashed: %s: %s" % (type(exc).__name__, exc)

            trace.observation(name, ok, observation)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": observation,
                }
            )

        if toolbox.finished:
            break

    snap = toolbox.snapshot()
    result = RunResult(
        ok=bool(toolbox.finished and snap["tests_green"]),
        finished=toolbox.finished,
        steps=steps,
        summary=toolbox.summary,
        out_dir=out_dir,
        files=list(snap["files"]),
        tests_green=bool(snap["tests_green"]),
        test_runs=int(snap["test_runs"]),
        backend=getattr(backend, "label", getattr(backend, "name", "unknown")),
        error=error,
    )
    trace.finish(result)
    return result
