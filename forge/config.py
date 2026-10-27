"""Configuration + environment handling for Forge.

Mode resolution (in order of precedence):
  1. ``--mock`` / ``--real`` on the command line
  2. ``FORGE_MODE=mock|real`` in the environment
  3. ``real`` when ``NEBIUS_API_KEY`` is set, otherwise ``mock``

Nothing here ever prints or stores the API key beyond passing it to the
HTTP layer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

# Verified 2026-10-27 against the official Nebius page:
# https://nebius.com/services/token-factory/nemotron
#   client = OpenAI(base_url="https://api.tokenfactory.us-central1.nebius.com/v1/",
#                   api_key=os.environ.get("NEBIUS_API_KEY"))
#   model  = "nvidia/nemotron-3-super-120b-a12b"
# Both values are overridable via env vars because provider endpoints move.
DEFAULT_BASE_URL = "https://api.tokenfactory.us-central1.nebius.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"

# Documented alternatives seen in the wild (UNVERIFIED as of 2026-10-27).
ALTERNATE_BASE_URLS = [
    "https://api.tokenfactory.nebius.com/v1",
    "https://api.tokenfactory.us-central1.nebius.com/v1",
]

# Candidate NVIDIA open-source model IDs on Token Factory (UNVERIFIED - check
# with `python -m forge --models` using your own key).
MODEL_CANDIDATES = [
    "nvidia/nemotron-3-super-120b-a12b",  # seen verbatim in Nebius docs sample
    "nvidia/nemotron-3-nano-30b-a3b",     # Nemotron 3 Nano, exact id UNVERIFIED
    "nvidia/nemotron-3-ultra-550b",       # Nemotron 3 Ultra, exact id UNVERIFIED
]

VALID_MODES = ("mock", "real")


class ConfigError(Exception):
    """Raised for bad configuration before any work starts."""


@dataclass
class Config:
    """Everything the agent loop needs to run."""

    goal: str
    out_dir: str = "build"
    mode: str = "mock"
    api_key: Optional[str] = None
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    max_steps: int = 12
    timeout: int = 120
    json_trace: Optional[str] = None
    color: bool = True

    @property
    def is_real(self) -> bool:
        return self.mode == "real"

    def redacted(self) -> dict:
        """Config as a dict safe to print / log (no secrets)."""
        return {
            "mode": self.mode,
            "base_url": self.base_url if self.is_real else "(offline)",
            "model": self.model if self.is_real else "scripted-demo",
            "max_steps": self.max_steps,
            "timeout_s": self.timeout,
            "api_key_present": bool(self.api_key),
        }


def resolve_mode(requested: Optional[str], api_key: Optional[str]) -> str:
    """Return the effective mode, raising ConfigError for contradictions."""
    env_mode = os.environ.get("FORGE_MODE", "").strip().lower() or None
    if requested and env_mode and requested != env_mode:
        raise ConfigError(
            "--%s contradicts FORGE_MODE=%s; pick one" % (requested, env_mode)
        )
    mode = requested or env_mode
    if mode is None:
        mode = "real" if api_key else "mock"
    if mode not in VALID_MODES:
        raise ConfigError("unknown mode %r (expected one of %s)" % (mode, VALID_MODES))
    if mode == "real" and not api_key:
        raise ConfigError(
            "real mode needs an API key. Set NEBIUS_API_KEY in your shell, or run "
            "with --mock for the offline demo.\n"
            "  export NEBIUS_API_KEY=...   # from Nebius Token Factory console"
        )
    return mode


def from_env(goal: str, **overrides) -> Config:
    """Build a Config from environment variables with CLI overrides."""
    api_key = os.environ.get("NEBIUS_API_KEY") or None
    mode = resolve_mode(overrides.pop("mode", None), api_key)
    defaults = dict(
        goal=goal,
        out_dir=os.environ.get("FORGE_OUT_DIR", "build"),
        mode=mode,
        api_key=api_key,
        base_url=(
            os.environ.get("NEBIUS_BASE_URL")
            or DEFAULT_BASE_URL
        ).rstrip("/"),
        model=os.environ.get("NEBIUS_MODEL") or DEFAULT_MODEL,
        max_steps=int(os.environ.get("FORGE_MAX_STEPS", "12")),
        timeout=int(os.environ.get("FORGE_TIMEOUT", "120")),
        json_trace=os.environ.get("FORGE_JSON_TRACE") or None,
        color=os.environ.get("NO_COLOR") is None,
    )
    defaults.update({k: v for k, v in overrides.items() if v is not None})
    if defaults["max_steps"] < 1:
        raise ConfigError("max_steps must be >= 1")
    if defaults["timeout"] < 5:
        raise ConfigError("timeout must be >= 5 seconds")
    return Config(**defaults)
