#!/usr/bin/env python3
"""socialdata-mcp — MCP stdio server wrapping socialdata.tools REST API.

This module is the runtime entrypoint. The actual implementation lives under
the :mod:`socialdata_mcp` package, organized as:

  config.py       — env-driven Config dataclass
  http.py         — async HTTP client + error mapping
  normalize.py    — pure tweet/user normalizers
  api/<resource>  — thin REST wrappers (search, users, tweets, lists,
                    communities, spaces, social_actions)
  tools/<resource>— @mcp.tool() wrappers (LLM-facing)

Auth: SOCIALDATA_API_KEY env var (required at first tool invocation).
Transport: stdio.
"""
from __future__ import annotations

import sys

from socialdata_mcp.config import ConfigError
from socialdata_mcp.tools import mcp
from socialdata_mcp.tools._registry import get_config


def main() -> None:
    try:
        get_config()
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
