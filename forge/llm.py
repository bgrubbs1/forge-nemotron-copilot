"""Model backends: Nebius Token Factory (real) and a scripted offline mock.

Both return an OpenAI-style assistant message dict, so the agent loop is
identical in both modes:

    {"role": "assistant",
     "content": "...optional narration...",
     "tool_calls": [{"id": "call_1", "type": "function",
                     "function": {"name": "write_file",
                                  "arguments": "{\\"path\\": ...}"}}]}

Real mode talks to the Nebius Token Factory OpenAI-compatible HTTP API with
``urllib`` only (no SDK, no dependencies).
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from . import demo_assets
from .config import Config


class BackendError(Exception):
    """The model call failed (network, auth, bad response)."""


def assistant_message(content: Optional[str], calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    msg: Dict[str, Any] = {"role": "assistant", "content": content or ""}
    if calls:
        msg["tool_calls"] = calls
    return msg


def _call(name: str, args: Dict[str, Any], call_id: str) -> Dict[str, Any]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


# ---------------------------------------------------------------------------
# Mock backend
# ---------------------------------------------------------------------------
class MockBackend:
    """Deterministic scripted trajectory. No network, no key, same loop.

    Step 4 really runs the tests on buggy code and really gets a non-zero exit
    code; step 6 re-runs them after the fix.
    """

    name = "mock"
    label = "scripted demo (offline)"

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._script = self._build_script()
        self._i = 0

    def _build_script(self) -> List[Dict[str, Any]]:
        return [
            assistant_message(
                "Plan: one module (tempconv.py), one unittest file, then verify with "
                "run_tests. Writing the spec first.",
                [_call("write_file", {"path": "SPEC.md", "content": demo_assets.SPEC_MD}, "call_mock_1")],
            ),
            assistant_message(
                "Now the module itself: Celsius/Fahrenheit/Kelvin helpers plus a small CLI.",
                [_call("write_file", {"path": "tempconv.py", "content": demo_assets.TEMPconv_V1}, "call_mock_2")],
            ),
            assistant_message(
                "And tests covering both directions, the Kelvin boundary and bad input.",
                [_call("write_file", {"path": "test_tempconv.py", "content": demo_assets.TEST_FILE}, "call_mock_3")],
            ),
            assistant_message(
                "Running the suite.",
                [_call("run_tests", {}, "call_mock_4")],
            ),
            assistant_message(
                "Three Kelvin assertions failed: my offset is 273 instead of 273.15 "
                "(-273.15 C should be 0 K). Patching the constant.",
                [_call("write_file", {"path": "tempconv.py", "content": demo_assets.TEMPconv_V2}, "call_mock_5")],
            ),
            assistant_message(
                "Re-running the suite to confirm the fix.",
                [_call("run_tests", {}, "call_mock_6")],
            ),
            assistant_message(
                "All green. Adding a short README with usage.",
                [_call("write_file", {"path": "README.md", "content": demo_assets.README_MD}, "call_mock_7")],
            ),
            assistant_message(
                "Suite is green and the README is written. Finishing.",
                [
                    _call(
                        "finish",
                        {
                            "summary": (
                                "Built tempconv, a dependency-free temperature converter "
                                "with a three-unit CLI. The first test run exposed a real "
                                "bug (Kelvin offset hardcoded to 273 instead of 273.15); the "
                                "agent patched the constant and the second run was green: all 7 tests "
                                "pass. Demo mode uses a scripted model "
                                "trajectory; in real mode the same loop is driven by "
                                "Nemotron on Nebius Token Factory."
                            )
                        },
                        "call_mock_8",
                    )
                ],
            ),
        ]

    def complete(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self._i >= len(self._script):
            # Script exhausted without finish: behave like a model that stalls.
            return assistant_message("Done.", [])
        msg = self._script[self._i]
        self._i += 1
        return msg


# ---------------------------------------------------------------------------
# Nebius Token Factory backend
# ---------------------------------------------------------------------------
class NebiusBackend:
    """OpenAI-compatible chat completions against Nebius Token Factory.

    Verified endpoint + model (2026-10-27, nebius.com/services/token-factory):
        base_url = https://api.tokenfactory.us-central1.nebius.com/v1/
        model    = nvidia/nemotron-3-super-120b-a12b
    Both are overridable via NEBIUS_BASE_URL / NEBIUS_MODEL.
    """

    name = "nebius"
    label = "Nebius Token Factory"

    def __init__(self, cfg: Config, max_retries: int = 2):
        if not cfg.api_key:
            raise BackendError("NEBIUS_API_KEY is not set")
        self.cfg = cfg
        self.max_retries = max_retries
        self.label = "Nebius Token Factory (%s)" % cfg.model

    # ---------------------------------------------------------------- helpers
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": "Bearer %s" % self.cfg.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "forge-agent/1.0 (+hackathon entry)",
        }

    def _request(self, method: str, path: str, payload: Optional[dict] = None) -> dict:
        url = self.cfg.base_url.rstrip("/") + path
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        last_err: Optional[str] = None
        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
            try:
                with urllib.request.urlopen(req, timeout=self.cfg.timeout) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw)
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:1200]
                last_err = "HTTP %s from %s\n%s" % (e.code, url, body)
                if e.code in (401, 403):
                    raise BackendError(
                        "authentication failed (HTTP %s). Check NEBIUS_API_KEY, and that "
                        "the key belongs to the endpoint in NEBIUS_BASE_URL.\n%s"
                        % (e.code, body)
                    )
                if e.code == 404:
                    raise BackendError(
                        "HTTP 404 for %s - the base URL or model id may be wrong.\n"
                        "Try `python -m forge --models` to list models on your key.\n%s"
                        % (url, body)
                    )
                if e.code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    continue
                raise BackendError(last_err)
            except urllib.error.URLError as e:
                last_err = "network error calling %s: %s" % (url, e.reason)
                if attempt < self.max_retries:
                    continue
                raise BackendError(last_err)
            except (TimeoutError, OSError) as e:  # pragma: no cover - env dependent
                last_err = "network error calling %s: %s" % (url, e)
                if attempt < self.max_retries:
                    continue
                raise BackendError(last_err)
        raise BackendError(last_err or "request failed")

    # ---------------------------------------------------------------- API
    def list_models(self) -> List[str]:
        payload = self._request("GET", "/models")
        rows = payload.get("data") or payload.get("models") or []
        ids = []
        for row in rows:
            if isinstance(row, dict):
                mid = row.get("id") or row.get("name")
                if mid:
                    ids.append(str(mid))
            elif isinstance(row, str):
                ids.append(row)
        return sorted(ids)

    def complete(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = {
            "model": self.cfg.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0.2,
            "max_tokens": 2048,
        }
        data = self._request("POST", "/chat/completions", payload)
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            raise BackendError("unexpected response shape: %s" % json.dumps(data)[:800])
        content = message.get("content")
        if isinstance(content, list):
            # Some servers return content as a list of parts.
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        calls = message.get("tool_calls") or []
        if not calls and content:
            calls = _parse_text_tool_calls(content)
            if calls:
                content = _strip_tool_json(content)
        normalised = []
        for i, call in enumerate(calls):
            fn = call.get("function") or {}
            name = fn.get("name")
            if not name:
                continue
            raw_args = fn.get("arguments")
            if isinstance(raw_args, dict):
                raw_args = json.dumps(raw_args)
            normalised.append(
                {
                    "id": call.get("id") or "call_%d" % (i + 1),
                    "type": "function",
                    "function": {"name": name, "arguments": raw_args or "{}"},
                }
            )
        return assistant_message(content, normalised)


_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S)


def _parse_text_tool_calls(content: str) -> List[Dict[str, Any]]:
    """Fallback for servers/models that describe a call in prose JSON.

    Accepts either a fenced block or a bare object containing a tool name plus
    an arguments/parameters object.
    """
    from .prompt import TOOL_NAMES

    candidates: List[str] = _FENCE_RE.findall(content)
    stripped = content.strip()
    if stripped.startswith("{"):
        candidates.append(stripped)
    calls = []
    for blob in candidates:
        try:
            obj = json.loads(blob)
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        name = obj.get("tool") or obj.get("name") or obj.get("function")
        args = obj.get("arguments", obj.get("parameters", obj.get("args", {})))
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                args = {}
        if name in TOOL_NAMES and isinstance(args, dict):
            calls.append(_call(name, args, "call_text_%d" % (len(calls) + 1)))
    return calls


def _strip_tool_json(content: str) -> str:
    """Drop a tool-call JSON block from the narration shown to the user."""
    stripped = content.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            if isinstance(json.loads(stripped), dict):
                return ""
        except ValueError:
            pass
    return _FENCE_RE.sub("", content).strip()


# ---------------------------------------------------------------------------
def make_backend(cfg: Config):
    if cfg.is_real:
        return NebiusBackend(cfg)
    return MockBackend(cfg)
