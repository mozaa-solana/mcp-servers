"""FastMCP singleton + lazy-loaded service.

Tool modules import :data:`mcp` to register themselves and ``get_service()``
so the heavy googleapiclient discovery + service-account credential loading
only runs on the first tool call (and is cached afterwards).
"""
from __future__ import annotations

from functools import lru_cache, wraps
from typing import Any, Awaitable, Callable

from googleapiclient.errors import HttpError
from mcp.server.fastmcp import FastMCP

from ..config import Config
from ..drive_client import DriveAPIError, build_docs_service, build_service, build_sheets_service, wrap_http_error
from ..safety import LocalPathViolation, SafetyViolation

mcp = FastMCP("gdrive")


def handle_drive_errors(
    fn: Callable[..., Awaitable[dict[str, Any]]],
) -> Callable[..., Awaitable[dict[str, Any]]]:
    """Decorator: convert known errors into the standard ``{"error": ...}`` MCP
    response so the agent gets a clean message instead of a raw traceback.

    Catches:
      - :class:`googleapiclient.errors.HttpError` → preserves HTTP status code.
      - :class:`DriveAPIError` (already wrapped at the api/* layer if used).
      - :class:`SafetyViolation` (working-folder rail).
      - :class:`LocalPathViolation` (local sandbox rail).

    Anything else (e.g. ``OSError``, ``ValueError`` from agent input) is left
    to propagate — those are bugs that should surface during testing, not
    runtime concerns to swallow.
    """

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return await fn(*args, **kwargs)
        except HttpError as exc:
            wrapped = wrap_http_error(exc)
            return {
                "error": str(wrapped.body) or wrapped.reason or "Drive API error",
                "status_code": wrapped.status_code,
            }
        except DriveAPIError as exc:
            return {
                "error": str(exc.body) or exc.reason or "Drive API error",
                "status_code": exc.status_code,
            }
        except SafetyViolation as exc:
            return {"error": str(exc), "violation": "working_folder"}
        except LocalPathViolation as exc:
            return {"error": str(exc), "violation": "local_sandbox"}

    return wrapper


@lru_cache(maxsize=1)
def get_config() -> Config:
    return Config.from_env()


@lru_cache(maxsize=1)
def get_service() -> Any:
    """Drive v3 service client (lazy, cached)."""
    return build_service(get_config())


@lru_cache(maxsize=1)
def get_sheets_service() -> Any:
    """Sheets v4 service client (lazy, cached)."""
    return build_sheets_service(get_config())


@lru_cache(maxsize=1)
def get_docs_service() -> Any:
    """Docs v1 service client (lazy, cached)."""
    return build_docs_service(get_config())


def reset_caches_for_tests() -> None:
    """Test hook — clear the lru_caches so monkey-patching takes effect."""
    get_config.cache_clear()
    get_service.cache_clear()
    get_sheets_service.cache_clear()
    get_docs_service.cache_clear()
