"""CLI entry point: ``python -m forge "your goal" [--mock|--real]``."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .agent import run_agent
from .config import (
    ALTERNATE_BASE_URLS,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    MODEL_CANDIDATES,
    Config,
    ConfigError,
    from_env,
)
from .llm import BackendError, NebiusBackend, make_backend
from .trace import Trace

DEMO_GOAL = "Build a CLI that converts temperatures between Celsius, Fahrenheit and Kelvin, with unit tests."


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="forge",
        description="Turn a natural-language goal into a runnable, tested Python project "
        "using NVIDIA Nemotron on Nebius Token Factory.",
    )
    p.add_argument("goal", nargs="?", help="what to build (natural language)")
    p.add_argument("--demo", action="store_true", help="use the built-in demo goal")
    p.add_argument("--mock", action="store_true", help="force the offline scripted backend")
    p.add_argument("--real", action="store_true", help="force Nebius Token Factory")
    p.add_argument("--out", default=None, help="sandbox/output directory (default: build)")
    p.add_argument("--max-steps", type=int, default=None, help="step budget (default: 12)")
    p.add_argument("--json", dest="json_trace", default=None, help="write a JSONL transcript here")
    p.add_argument("--models", action="store_true", help="list models available to your API key, then exit")
    p.add_argument("--version", action="version", version="forge %s" % __version__)
    return p


def _mode_flags(args) -> str | None:
    if args.mock and args.real:
        raise ConfigError("pick one of --mock or --real")
    if args.mock:
        return "mock"
    if args.real:
        return "real"
    return None


def cmd_list_models(mode: str | None) -> int:
    """`--models`: ask the live API, or print the documented candidates offline."""
    try:
        cfg = from_env(DEMO_GOAL, mode=mode)
    except ConfigError:
        cfg = Config(goal=DEMO_GOAL, mode="mock")
    if cfg.is_real:
        backend = NebiusBackend(cfg)
        print("GET %s/models" % cfg.base_url)
        try:
            ids = backend.list_models()
        except BackendError as exc:
            print("ERROR: %s" % exc, file=sys.stderr)
            return 1
        if not ids:
            print("(endpoint returned no models)")
        for mid in ids:
            marker = "  <-- configured NEBIUS_MODEL" if mid == cfg.model else ""
            print("  %s%s" % (mid, marker))
        if cfg.model not in ids:
            print(
                "\nWARNING: your NEBIUS_MODEL (%s) is not in the list above. Copy an "
                "exact id from the list into NEBIUS_MODEL." % cfg.model,
                file=sys.stderr,
            )
            return 1
        return 0
    print("Offline mode - documented endpoint and model ids (no key needed):")
    print("  NEBIUS_BASE_URL default : %s" % DEFAULT_BASE_URL)
    for alt in ALTERNATE_BASE_URLS:
        print("    alternate (UNVERIFIED): %s" % alt)
    print("  NEBIUS_MODEL default    : %s" % DEFAULT_MODEL)
    print("  NVIDIA Nemotron options (check exact ids with a real key):")
    for mid in MODEL_CANDIDATES:
        print("    %s" % mid)
    print("\nRun `NEBIUS_API_KEY=... python -m forge --models --real` to list live models.")
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        mode = _mode_flags(args)
    except ConfigError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    if args.models:
        return cmd_list_models(mode)

    goal = DEMO_GOAL if (args.demo or not args.goal) else args.goal
    overrides = {
        "mode": mode,
        "out_dir": args.out,
        "max_steps": args.max_steps,
        "json_trace": args.json_trace,
    }
    try:
        cfg = from_env(goal, **overrides)
    except ConfigError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    try:
        backend = make_backend(cfg)
    except BackendError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    trace = Trace(color=cfg.color, jsonl_path=cfg.json_trace)
    try:
        result = run_agent(cfg, backend, trace)
    finally:
        trace.close()

    if result.error:
        print("\nHint: if the endpoint or model id moved, check `python -m forge --models --real`.",
              file=sys.stderr)
        return 1

    if not cfg.is_real:
        print(
            "\n(mock mode: the loop above is real code; only the model is scripted. "
            "Set NEBIUS_API_KEY and add --real for Nemotron on Nebius Token Factory.)"
        )
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
