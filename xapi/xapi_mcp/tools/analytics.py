"""Per-tweet analytics tools — liking_users, retweeters, quote_tweets,
replies, and a richer metrics lookup for OWN tweets."""
from __future__ import annotations

import asyncio
from typing import Any

from .. import cost
from ..api import analytics as api_analytics
from ..api import search as api_search
from ..normalize import paginated, trim_tweet, trim_user
from ..normalize import _to_dict  # type: ignore[attr-defined]
from ._registry import get_budget, get_client, handle_x_errors, mcp


@mcp.tool()
@handle_x_errors
async def x_get_tweet_metrics(tweet_id: str) -> dict[str, Any]:
    """Lookup a tweet with full metrics blocks (public, non_public, organic).

    ``non_public_metrics`` + ``organic_metrics`` (impressions, profile_clicks,
    url_link_clicks, video_views) are populated **only when the tweet is
    authored by the authenticated user**. For other authors only
    ``public_metrics`` will be present.

    Cost ≈ $0.001 (owned read) for own tweets, $0.005 otherwise — pricing
    here uses the cheaper tier; X bills the actual rate."""
    cost_usd = cost.COST_OWNED_READ
    get_budget().check(cost_usd)
    raw = await asyncio.to_thread(
        api_analytics.get_tweet_with_metrics, get_client(), tweet_id
    )
    get_budget().record(cost_usd)
    d = _to_dict(raw)
    return {
        "id": d.get("id"),
        "text": d.get("text"),
        "created_at": d.get("created_at"),
        "author_id": d.get("author_id"),
        "public_metrics": d.get("public_metrics"),
        "non_public_metrics": d.get("non_public_metrics"),
        "organic_metrics": d.get("organic_metrics"),
        "estimated_cost_usd": cost_usd,
    }


@mcp.tool()
@handle_x_errors
async def x_get_liking_users(
    tweet_id: str, max_results: int = 100, cursor: str | None = None
) -> dict[str, Any]:
    """List users who liked a tweet (1–100). Cost ≈ $0.005 per user.
    For own tweets this can audit who's engaging."""
    n = max(1, min(max_results, 100))
    cost_usd = cost.COST_STANDARD_READ * n
    get_budget().check(cost_usd)
    raw = await asyncio.to_thread(
        api_analytics.get_liking_users, get_client(),
        tweet_id, max_results, cursor,
    )
    get_budget().record(cost_usd)
    out = paginated(raw["items"], raw["next_cursor"], trim_user)
    out["estimated_cost_usd"] = round(cost_usd, 4)
    return out


@mcp.tool()
@handle_x_errors
async def x_get_retweeters(
    tweet_id: str, max_results: int = 100, cursor: str | None = None
) -> dict[str, Any]:
    """List users who retweeted a tweet (1–100). Cost ≈ $0.005 per user."""
    n = max(1, min(max_results, 100))
    cost_usd = cost.COST_STANDARD_READ * n
    get_budget().check(cost_usd)
    raw = await asyncio.to_thread(
        api_analytics.get_retweeters, get_client(),
        tweet_id, max_results, cursor,
    )
    get_budget().record(cost_usd)
    out = paginated(raw["items"], raw["next_cursor"], trim_user)
    out["estimated_cost_usd"] = round(cost_usd, 4)
    return out


@mcp.tool()
@handle_x_errors
async def x_get_quote_tweets(
    tweet_id: str, max_results: int = 10, cursor: str | None = None
) -> dict[str, Any]:
    """List tweets that quote-tweeted the given tweet (10–100).
    Cost ≈ $0.005 per quote tweet. Useful for tracking how a post is
    being shared with commentary."""
    n = max(10, min(max_results, 100))
    cost_usd = cost.COST_STANDARD_READ * n
    get_budget().check(cost_usd)
    raw = await asyncio.to_thread(
        api_analytics.get_quote_tweets, get_client(),
        tweet_id, max_results, cursor,
    )
    get_budget().record(cost_usd)
    out = paginated(raw["items"], raw["next_cursor"], trim_tweet)
    out["estimated_cost_usd"] = round(cost_usd, 4)
    return out


@mcp.tool()
@handle_x_errors
async def x_get_replies(
    tweet_id: str, max_results: int = 10, cursor: str | None = None
) -> dict[str, Any]:
    """List replies in the same conversation thread (10–100).

    Implementation: searches recent tweets with ``conversation_id:<id>``.
    Caveats:
    - Only the last ~7 days are indexed by recent search.
    - Costs $0.005 per reply returned — large threads burn budget fast.
    - Cap ``max_results`` and use ``cursor`` to paginate consciously."""
    n = max(10, min(max_results, 100))
    cost_usd = cost.COST_STANDARD_READ * n
    get_budget().check(cost_usd)
    query = f"conversation_id:{tweet_id} -is:retweet"
    raw = await asyncio.to_thread(
        api_search.recent, get_client(), query,
        max_results=max_results, cursor=cursor,
    )
    get_budget().record(cost_usd)
    out = paginated(raw["items"], raw["next_cursor"], trim_tweet)
    out["estimated_cost_usd"] = round(cost_usd, 4)
    return out
