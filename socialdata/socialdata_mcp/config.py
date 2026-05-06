"""Runtime configuration loaded from environment variables.

The :class:`Config` dataclass is immutable; the loader fails fast when a required
secret is missing so that the MCP server never starts up half-configured.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_BASE_URL = "https://api.socialdata.tools"
DEFAULT_TIMEOUT_SECONDS = 30.0


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str
    timeout_seconds: float

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Config":
        env = env if env is not None else dict(os.environ)
        api_key = env.get("SOCIALDATA_API_KEY", "").strip()
        if not api_key:
            raise ConfigError("SOCIALDATA_API_KEY env var required")

        base_url = env.get("SOCIALDATA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

        try:
            timeout = float(env.get("SOCIALDATA_TIMEOUT", DEFAULT_TIMEOUT_SECONDS))
        except ValueError as exc:
            raise ConfigError(f"SOCIALDATA_TIMEOUT must be numeric: {exc}") from exc

        return cls(api_key=api_key, base_url=base_url, timeout_seconds=timeout)
