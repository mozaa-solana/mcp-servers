"""Diagnostic tool: report the current daily budget status."""
from __future__ import annotations

from typing import Any

from ._registry import get_budget, get_config, handle_x_errors, mcp


@mcp.tool()
@handle_x_errors
async def x_budget_status() -> dict[str, Any]:
    """Return today's USD spend, cap, and remaining headroom.

    The counter is in-memory only — restarting the MCP server zeroes it.
    Pricing source: https://docs.x.com/x-api/getting-started/pricing"""
    cfg = get_config()
    snap = get_budget().snapshot()
    return {
        **snap,
        "handle": cfg.handle,
        "dry_run": cfg.dry_run,
    }
