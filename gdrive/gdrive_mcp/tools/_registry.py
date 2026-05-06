"""FastMCP singleton + lazy-loaded service.

Tool modules import :data:`mcp` to register themselves and ``get_service()``
so the heavy googleapiclient discovery + service-account credential loading
only runs on the first tool call (and is cached afterwards).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..config import Config
from ..drive_client import build_service, build_sheets_service

mcp = FastMCP("gdrive")


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


def reset_caches_for_tests() -> None:
    """Test hook — clear the lru_caches so monkey-patching takes effect."""
    get_config.cache_clear()
    get_service.cache_clear()
    get_sheets_service.cache_clear()
