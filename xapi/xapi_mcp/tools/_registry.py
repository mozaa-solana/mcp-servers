"""Singletons + the ``handle_x_errors`` decorator shared by all tool modules.

Lazy-initialized via ``functools.lru_cache`` so importing the package is
side-effect-free (tests can patch the factories without touching env)."""
from __future__ import annotations

from functools import lru_cache, wraps
from typing import Any, Awaitable, Callable

from mcp.server.fastmcp import FastMCP

from ..budget import BudgetExceeded, DailyBudget
from ..config import Config
from ..x_client import XAPIError, XClient, build_client, wrap_tweepy_error

mcp = FastMCP("xapi")


@lru_cache(maxsize=1)
def get_config() -> Config:
    return Config.from_env()


@lru_cache(maxsize=1)
def get_client() -> XClient:
    return build_client(get_config())


@lru_cache(maxsize=1)
def get_budget() -> DailyBudget:
    return DailyBudget(cap_usd=get_config().budget_usd_per_day)


# Tweepy raises a hierarchy under tweepy.errors.TweepyException.
# Import lazily so test environments without tweepy installed (unlikely
# but possible) don't break import-time.
def _tweepy_exception_class() -> type[BaseException]:
    try:
        from tweepy.errors import TweepyException
        return TweepyException
    except Exception:
        return Exception


def handle_x_errors(fn: Callable[..., Awaitable[dict[str, Any]]]):
    """Convert tweepy errors + budget violations into LLM-friendly dicts.

    Tools wrapped with this decorator return a normal dict on success,
    or ``{"error": "...", "status_code": N}`` on failure — never raise."""
    TweepyException = _tweepy_exception_class()

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return await fn(*args, **kwargs)
        except BudgetExceeded as exc:
            return {"error": str(exc), "violation": "budget"}
        except XAPIError as exc:
            return {
                "error": str(exc),
                "status_code": exc.status_code,
                "body": exc.body,
            }
        except TweepyException as exc:  # type: ignore[misc]
            wrapped = wrap_tweepy_error(exc)
            return {
                "error": str(wrapped),
                "status_code": wrapped.status_code,
                "body": wrapped.body,
            }

    return wrapper
