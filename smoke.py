#!/usr/bin/env python3
"""Forge smoke test - end-to-end proof that the app works with no API key.

    python3 smoke.py          (or: make smoke)

Checks, in order:
  1. Python >= 3.9
  2. every module byte-compiles
  3. the unit test suite passes (mock + real-mode HTTP path)
  4. a full mock-mode agent run builds a project and exits PASS
  5. the generated project's own tests pass when run independently
  6. the generated CLI produces the documented output
  7. the JSONL transcript is well formed and contains no secrets
  8. no network is required (mock backend only)

Exit code 0 = all checks passed. Prints one PASS/FAIL line per check.
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

REPO = os.path.dirname(os.path.abspath(__file__))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn

    return deco


def _run(cmd, cwd, timeout=180, env=None):
    return subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        env=env,
    )


@check("python >= 3.9")
def _python(_):
    if sys.version_info < (3, 9):
        raise AssertionError("need Python 3.9+, found %s" % sys.version.split()[0])
    return sys.version.split()[0]


@check("all modules byte-compile")
def _compile(_):
    files = []
    for base in ("forge", "tests"):
        for dirpath, _d, names in os.walk(os.path.join(REPO, base)):
            for n in names:
                if n.endswith(".py"):
                    path = os.path.join(dirpath, n)
                    with open(path, "r", encoding="utf-8") as fh:
                        ast.parse(fh.read(), filename=path)
                    files.append(os.path.relpath(path, REPO))
    files.append("smoke.py")
    return "%d files" % len(files)


@check("unit test suite")
def _unit(_):
    proc = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], REPO)
    out = proc.stdout.decode(errors="replace")
    if proc.returncode != 0:
        raise AssertionError("unit tests failed:\n" + out[-4000:])
    tail = [ln for ln in out.splitlines() if ln.startswith("Ran ")]
    return tail[-1] if tail else "ok"


@check("mock-mode agent run (end to end)")
def _agent(tmp):
    from forge.agent import run_agent
    from forge.config import Config
    from forge.llm import MockBackend, make_backend
    from forge.trace import Trace

    out_dir = os.path.join(tmp, "demo-build")
    cfg = Config(goal="Build a CLI that converts temperatures between C, F and K, with unit tests.",
                 mode="mock", out_dir=out_dir, max_steps=12)
    backend = make_backend(cfg)
    if getattr(backend, "name", "") != "mock":
        raise AssertionError("expected the mock backend, got %r" % getattr(backend, "name", None))
    trace = Trace(stream=open(os.path.join(tmp, "stdout.txt"), "w"), color=False)
    try:
        result = run_agent(cfg, backend, trace)
    finally:
        trace.close()
    if not result.ok:
        raise AssertionError("agent run did not end green: %r" % (result,))
    if result.test_runs != 2:
        raise AssertionError("expected 2 test runs (fail then pass), got %d" % result.test_runs)
    missing = [f for f in ("tempconv.py", "test_tempconv.py", "README.md", "SPEC.md")
               if not os.path.isfile(os.path.join(out_dir, f))]
    if missing:
        raise AssertionError("missing generated files: %s" % missing)
    _agent.out_dir = out_dir
    return "%d steps, %d files, %d test runs" % (result.steps, len(result.files), result.test_runs)


@check("generated project passes its own tests")
def _generated(_):
    out_dir = getattr(_agent, "out_dir", None)
    if not out_dir or not os.path.isdir(out_dir):
        raise AssertionError("no generated project to test")
    proc = _run([sys.executable, "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"], out_dir)
    if proc.returncode != 0:
        raise AssertionError("generated tests failed:\n" + proc.stdout.decode()[-3000:])
    tail = [ln for ln in proc.stdout.decode().splitlines() if ln.startswith("Ran ")]
    return tail[-1] if tail else "ok"


@check("generated CLI output is correct")
def _cli(_):
    out_dir = _agent.out_dir
    proc = _run([sys.executable, "tempconv.py", "100", "C", "F"], out_dir, timeout=60)
    got = proc.stdout.decode().strip()
    if got != "100C = 212F":
        raise AssertionError("expected '100C = 212F', got %r" % got)
    return got


@check("JSONL transcript well formed, no secrets")
def _trace(tmp):
    from forge.agent import run_agent
    from forge.config import Config
    from forge.llm import MockBackend
    from forge.trace import Trace

    path = os.path.join(tmp, "trace.jsonl")
    cfg = Config(goal="demo", mode="mock", out_dir=os.path.join(tmp, "t2"), max_steps=12)
    trace = Trace(stream=open(os.path.join(tmp, "stdout2.txt"), "w"), color=False, jsonl_path=path)
    try:
        run_agent(cfg, MockBackend(cfg), trace)
    finally:
        trace.close()
    with open(path, encoding="utf-8") as fh:
        events = [json.loads(line) for line in fh if line.strip()]
    kinds = [e["event"] for e in events]
    if "run_complete" not in kinds:
        raise AssertionError("no run_complete event")
    if not [e for e in events if e["event"] == "run_complete"][0]["ok"]:
        raise AssertionError("run_complete says not ok")
    blob = json.dumps(events)
    for marker in ("NEBIUS_API_KEY", "Bearer ", "test-key", "sk-"):
        if marker in blob:
            raise AssertionError("possible secret leaked into transcript: %r" % marker)
    return "%d events" % len(events)


@check("real-mode HTTP path (local fake endpoint)")
def _real_http(tmp):
    sys.path.insert(0, os.path.join(REPO, "tests"))
    from fake_nebius_server import FakeNebiusServer
    from forge.agent import run_agent
    from forge.llm import NebiusBackend, make_backend
    from forge.trace import Trace

    with FakeNebiusServer() as srv:
        cfg = srv.config(out_dir=os.path.join(tmp, "real-build"), max_steps=12)
        backend = make_backend(cfg)
        if not isinstance(backend, NebiusBackend):
            raise AssertionError("expected NebiusBackend, got %r" % type(backend).__name__)
        trace = Trace(stream=open(os.path.join(tmp, "stdout-real.txt"), "w"), color=False)
        try:
            result = run_agent(cfg, backend, trace)
        finally:
            trace.close()
        if not result.ok:
            raise AssertionError("real-mode HTTP run did not end green")
        if len(srv.requests) != 8:
            raise AssertionError("expected 8 HTTP calls, saw %d" % len(srv.requests))
    return "8 OpenAI-compatible HTTP calls, green"


@check("real mode needs a key (fails safely)")
def _real_requires_key(_):
    env = {k: v for k, v in os.environ.items() if k != "NEBIUS_API_KEY"}
    env["NO_COLOR"] = "1"
    proc = _run([sys.executable, "-m", "forge", "--demo", "--real"], REPO, timeout=60, env=env)
    if proc.returncode != 2:
        raise AssertionError("expected exit 2, got %d" % proc.returncode)
    out = proc.stdout.decode(errors="replace")
    if "NEBIUS_API_KEY" not in out:
        raise AssertionError("no guidance about NEBIUS_API_KEY")
    return "exit 2 + guidance"


def main() -> int:
    print("=" * 70)
    print(" FORGE SMOKE TEST  -  offline, no API key, no network")
    print("=" * 70)
    tmp = tempfile.mkdtemp(prefix="forge-smoke-")
    failures = 0
    try:
        for name, fn in CHECKS:
            try:
                detail = fn(tmp)
                print("  PASS  %-46s %s" % (name, detail or ""))
            except Exception as exc:
                failures += 1
                print("  FAIL  %-46s %s" % (name, exc))
                if os.environ.get("FORGE_SMOKE_VERBOSE"):
                    traceback.print_exc()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("-" * 70)
    if failures:
        print(" SMOKE FAILED: %d check(s) failed" % failures)
        return 1
    print(" SMOKE PASS: %d/%d checks green" % (len(CHECKS), len(CHECKS)))
    print(" Next: add NEBIUS_API_KEY and run `make real` for the Nemotron path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
