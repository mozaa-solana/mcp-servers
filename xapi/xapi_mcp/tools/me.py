"""Owned-read tools: cheap ($0.001 / call) and side-effect-free."""
from __future__ import annotations

import asyncio
from typing import Any

from .. import cost
from ..api import me as api_me
from ..normalize import paginated, trim_tweet, trim_user
from ._registry import get_budget, get_client, handle_x_errors, mcp


@mcp.tool()
@handle_x_errors
async def x_get_me() -> dict[str, Any]:
    """Return the authenticated user's profile (handle, display name, bio,
    follower counts). Cost ≈ $0.001 (owned read). Idempotent, side-effect-free."""
    cost_usd = cost.COST_OWNED_READ
    get_budget().check(cost_usd)
    raw = await asyncio.to_thread(api_me.get_me, get_client())
    get_budget().record(cost_usd)
    return {**trim_user(raw), "estimated_cost_usd": cost_usd}


@mcp.tool()
@handle_x_errors
async def x_get_my_recent_posts(max_results: int = 10) -> dict[str, Any]:
    """List the authenticated user's recent tweets (5–100). Cost ≈ $0.001
    per tweet returned (owned reads). Returns ``{count, items[], next_cursor}``."""
    cost_usd = cost.COST_OWNED_READ * max(5, min(max_results, 100))
    get_budget().check(cost_usd)
    raw = await asyncio.to_thread(api_me.get_my_recent_posts, get_client(), max_results)
    get_budget().record(cost_usd)
    out = paginated(raw["items"], raw["next_cursor"], trim_tweet)
    out["estimated_cost_usd"] = round(cost_usd, 4)
    return out
