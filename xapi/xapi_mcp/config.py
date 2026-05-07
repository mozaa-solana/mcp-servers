"""Env-driven config for the X API MCP server.

Single-user model: each process holds exactly one user's OAuth 1.0a
access token. Multi-user is achieved by registering N MCP server configs
in Goclaw (see README).
"""
from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised at startup when required env is missing or malformed."""


@dataclass(frozen=True)
class Config:
    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str
    handle: str | None
    budget_usd_per_day: float | None
    dry_run: bool

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Config":
        e = env if env is not None else dict(os.environ)

        required = (
            "X_API_KEY",
            "X_API_SECRET",
            "X_ACCESS_TOKEN",
            "X_ACCESS_TOKEN_SECRET",
        )
        missing = [k for k in required if not e.get(k, "").strip()]
        if missing:
            raise ConfigError(
                f"Missing required env: {', '.join(missing)}. "
                "Generate OAuth 1.0a credentials at developer.x.com → "
                "your app → Keys & Tokens → Access Token and Secret."
            )

        budget_raw = e.get("X_BUDGET_USD_PER_DAY", "").strip()
        if budget_raw:
            try:
                budget = float(budget_raw)
                if budget < 0:
                    raise ValueError
            except ValueError:
                raise ConfigError(
                    f"X_BUDGET_USD_PER_DAY must be a non-negative number, got {budget_raw!r}"
                ) from None
        else:
            budget = None

        dry_run = e.get("X_DRY_RUN", "").strip().lower() in ("1", "true", "yes")

        handle = e.get("X_HANDLE", "").strip() or None

        return cls(
            api_key=e["X_API_KEY"].strip(),
            api_secret=e["X_API_SECRET"].strip(),
            access_token=e["X_ACCESS_TOKEN"].strip(),
            access_token_secret=e["X_ACCESS_TOKEN_SECRET"].strip(),
            handle=handle,
            budget_usd_per_day=budget,
            dry_run=dry_run,
        )
