"""FastMCP singleton + lazy-loaded :class:`Config`.

Tools import :data:`mcp` to register themselves and :func:`get_config` so the
config (and the env-var validation it does) is evaluated only on first call,
which keeps tests free of mandatory env setup at import time.
"""
from __future__ import annotations

from functools import lru_cache

from mcp.server.fastmcp import FastMCP

from ..config import Config

mcp = FastMCP("socialdata-twitter")


@lru_cache(maxsize=1)
def get_config() -> Config:
    return Config.from_env()
