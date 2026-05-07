"""MCP stdio entrypoint for the X (Twitter) API adapter.

Run via Goclaw or any MCP-compatible host. Spawn one process per X user
(Cách 1 multi-user model — see README).
"""
from __future__ import annotations

from xapi_mcp.tools import _registry  # noqa: F401  - imports mcp singleton
from xapi_mcp import tools as _tools_pkg  # noqa: F401  - registers @mcp.tool()


def main() -> None:
    _registry.mcp.run()


if __name__ == "__main__":
    main()
