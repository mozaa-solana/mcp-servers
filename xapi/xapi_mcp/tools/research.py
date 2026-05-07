"""Research / discovery tools — search, user-tweet lookup, trends.

Cost warning: standard reads are $0.005 each. Default max_results stays
low (10) and tools accept ``cursor`` for pagination so callers can
explicitly opt into spend.

For bulk research without per-call cost, prefer the ``socialdata`` MCP
server (scraping-based, no quota)."""
from __future__ import annotations

import asyncio
from typing import Any

from .. import cost
from ..api import posts as api_posts
from ..api import search as api_search
from ..api import trends as api_trends
from ..api import users as api_users
from ..normalize import paginated, trim_tweet, trim_user
from ._registry import get_budget, get_client, handle_x_errors, mcp
from .users import _resolve_user_id


@mcp.tool()
@handle_x_errors
async def x_search_recent_tweets(
    query: str, max_results: int = 10, cursor: str | None = None
) -> dict[str, Any]:
    """Search tweets posted in the last 7 days.

    Query supports X's search operators: ``from:user``, ``#tag``, ``"phrase"``,
    ``-exclude``, ``conversation_id:ID``, ``lang:vi``. Cost ≈ $0.005 per
    tweet returned (10 returned by default → $0.05). Returns
    ``{count, items[], next_cursor}``.
    """
    n = max(10, min(max_results, 100))
    cost_usd = cost.COST_STANDARD_READ * n
    get_budget().check(cost_usd)
    raw = await asyncio.to_thread(
        api_search.recent, get_client(), query,
        max_results=max_results, cursor=cursor,
    )
    get_budget().record(cost_usd)
    out = paginated(raw["items"], raw["next_cursor"], trim_tweet)
    out["estimated_cost_usd"] = round(cost_usd, 4)
    return out


@mcp.tool()
@handle_x_errors
async def x_get_user_recent_posts(
    handle_or_id: str, max_results: int = 10
) -> dict[str, Any]:
    """List a user's recent tweets (5–100). Pass ``@handle`` or numeric id.
    Cost ≈ $0.005 per tweet returned."""
    n = max(5, min(max_results, 100))
    cost_usd = cost.COST_STANDARD_READ * n
    get_budget().check(cost_usd)
    target_id = await _resolve_user_id(handle_or_id)
    raw = await asyncio.to_thread(
        api_posts.get_user_tweets, get_client(), target_id, max_results
    )
    get_budget().record(cost_usd)
    out = paginated(raw["items"], raw["next_cursor"], trim_tweet)
    out["estimated_cost_usd"] = round(cost_usd, 4)
    return out


@mcp.tool()
@handle_x_errors
async def x_get_trending_topics(woeid: int = 1) -> dict[str, Any]:
    """Trending topics for a location. ``woeid=1`` is worldwide.

    Other examples: ``23424975`` (UK), ``23424977`` (US), ``23424984`` (Vietnam).
    NOTE: this is a v1.1 endpoint and access tier has changed over time —
    if X returns 403 you may need a higher tier."""
    raw = await asyncio.to_thread(api_trends.get_place_trends, get_client(), woeid)
    return {
        "count": len(raw),
        "items": [
            {k: t.get(k) for k in ("name", "url", "tweet_volume") if k in t}
            for t in raw
        ],
        "estimated_cost_usd": 0.0,
    }


@mcp.tool()
@handle_x_errors
async def x_get_user_followers(
    handle_or_id: str, max_results: int = 100, cursor: str | None = None
) -> dict[str, Any]:
    """List a user's followers (1–1000) — for OTHER users (not the
    authenticated user). For your own followers use ``x_get_my_followers``
    (cheaper). Cost ≈ $0.005 per follower returned."""
    n = max(1, min(max_results, 1000))
    cost_usd = cost.COST_STANDARD_READ * n
    get_budget().check(cost_usd)
    target_id = await _resolve_user_id(handle_or_id)
    raw = await asyncio.to_thread(
        api_users.get_followers, get_client(), target_id,
        max_results=max_results, cursor=cursor,
    )
    get_budget().record(cost_usd)
    out = paginated(raw["items"], raw["next_cursor"], trim_user)
    out["estimated_cost_usd"] = round(cost_usd, 4)
    return out
