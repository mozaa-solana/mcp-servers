"""Bookmark tools — owned tier ($0.001 read, $0.015 write)."""
from __future__ import annotations

import asyncio
from typing import Any

from .. import cost
from ..api import bookmarks as api_bookmarks
from ..normalize import paginated, trim_tweet
from ._registry import get_budget, get_client, get_config, handle_x_errors, mcp


@mcp.tool()
@handle_x_errors
async def x_bookmark_tweet(tweet_id: str) -> dict[str, Any]:
    """Save a tweet to the authenticated user's bookmarks. Cost ≈ $0.015."""
    cost_usd = cost.COST_ENGAGEMENT
    get_budget().check(cost_usd)
    if get_config().dry_run:
        return {"dry_run": True, "would_bookmark": tweet_id}
    raw = await asyncio.to_thread(api_bookmarks.add, get_client(), tweet_id)
    get_budget().record(cost_usd)
    return {"bookmarked": True, "id": tweet_id, "raw": raw, "estimated_cost_usd": cost_usd}


@mcp.tool()
@handle_x_errors
async def x_remove_bookmark(tweet_id: str) -> dict[str, Any]:
    """Remove a tweet from bookmarks. Cost ≈ $0.001 (owned)."""
    cost_usd = cost.COST_OWNED_READ
    get_budget().check(cost_usd)
    if get_config().dry_run:
        return {"dry_run": True, "would_remove_bookmark": tweet_id}
    raw = await asyncio.to_thread(api_bookmarks.remove, get_client(), tweet_id)
    get_budget().record(cost_usd)
    return {"removed": True, "id": tweet_id, "raw": raw, "estimated_cost_usd": cost_usd}


@mcp.tool()
@handle_x_errors
async def x_get_my_bookmarks(max_results: int = 10) -> dict[str, Any]:
    """List the authenticated user's bookmarks (5–100). Owned read.
    Cost ≈ $0.001 per bookmark returned."""
    n = max(5, min(max_results, 100))
    cost_usd = cost.COST_OWNED_READ * n
    get_budget().check(cost_usd)
    raw = await asyncio.to_thread(api_bookmarks.list_, get_client(), max_results)
    get_budget().record(cost_usd)
    out = paginated(raw["items"], raw["next_cursor"], trim_tweet)
    out["estimated_cost_usd"] = round(cost_usd, 4)
    return out
