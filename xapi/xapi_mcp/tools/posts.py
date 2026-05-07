"""Post-related tools: create, delete, like, retweet (and reverses).

Pricing reminder for create_tweet:
- Plain text/media post: ~$0.015
- Post containing a URL:  ~$0.20 (13× more)
- The cost estimate auto-detects URLs in ``text``."""
from __future__ import annotations

import asyncio
from typing import Any

from .. import cost
from ..api import posts as api_posts
from ..normalize import trim_tweet
from ._registry import get_budget, get_client, get_config, handle_x_errors, mcp


@mcp.tool()
@handle_x_errors
async def x_post_tweet(
    text: str,
    reply_to_tweet_id: str | None = None,
    quote_tweet_id: str | None = None,
    media_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Publish a new tweet on behalf of the authenticated user.

    Args:
        text: 1–280 chars (Premium accounts up to 25,000). Containing a URL
            triggers the 13× link-tax — keep links out unless necessary.
        reply_to_tweet_id: Make this a reply to the given tweet.
        quote_tweet_id: Make this a quote-tweet of the given tweet.
        media_ids: Up to 4 media IDs from ``x_upload_media``.

    Returns the created tweet ``{id, text, estimated_cost_usd}`` or an
    error dict. Honours ``X_DRY_RUN=1`` (returns shape without posting).
    """
    if not text or not text.strip():
        return {"error": "text must not be empty"}
    cost_usd = cost.estimate_post_cost(text)
    get_budget().check(cost_usd)

    cfg = get_config()
    if cfg.dry_run:
        return {
            "dry_run": True,
            "would_post": text,
            "reply_to_tweet_id": reply_to_tweet_id,
            "quote_tweet_id": quote_tweet_id,
            "media_ids": media_ids,
            "estimated_cost_usd": cost_usd,
        }

    raw = await asyncio.to_thread(
        api_posts.create,
        get_client(),
        text,
        reply_to_tweet_id=reply_to_tweet_id,
        quote_tweet_id=quote_tweet_id,
        media_ids=media_ids,
    )
    get_budget().record(cost_usd)
    return {**trim_tweet(raw), "estimated_cost_usd": cost_usd}


@mcp.tool()
@handle_x_errors
async def x_delete_tweet(tweet_id: str) -> dict[str, Any]:
    """Permanently delete a tweet authored by the authenticated user.
    Cannot be undone. No charge per X's docs (treated as engagement)."""
    cost_usd = cost.COST_ENGAGEMENT
    get_budget().check(cost_usd)
    cfg = get_config()
    if cfg.dry_run:
        return {"dry_run": True, "would_delete": tweet_id}
    raw = await asyncio.to_thread(api_posts.delete, get_client(), tweet_id)
    get_budget().record(cost_usd)
    return {"deleted": True, "id": tweet_id, "raw": raw, "estimated_cost_usd": cost_usd}


@mcp.tool()
@handle_x_errors
async def x_like_tweet(tweet_id: str) -> dict[str, Any]:
    """Like a tweet as the authenticated user. Cost ≈ $0.015."""
    cost_usd = cost.COST_ENGAGEMENT
    get_budget().check(cost_usd)
    if get_config().dry_run:
        return {"dry_run": True, "would_like": tweet_id}
    raw = await asyncio.to_thread(api_posts.like, get_client(), tweet_id)
    get_budget().record(cost_usd)
    return {"liked": True, "id": tweet_id, "raw": raw, "estimated_cost_usd": cost_usd}


@mcp.tool()
@handle_x_errors
async def x_unlike_tweet(tweet_id: str) -> dict[str, Any]:
    """Remove a like from a tweet. Cost ≈ $0.015."""
    cost_usd = cost.COST_ENGAGEMENT
    get_budget().check(cost_usd)
    if get_config().dry_run:
        return {"dry_run": True, "would_unlike": tweet_id}
    raw = await asyncio.to_thread(api_posts.unlike, get_client(), tweet_id)
    get_budget().record(cost_usd)
    return {"unliked": True, "id": tweet_id, "raw": raw, "estimated_cost_usd": cost_usd}


@mcp.tool()
@handle_x_errors
async def x_retweet(tweet_id: str) -> dict[str, Any]:
    """Retweet a tweet as the authenticated user. Cost ≈ $0.015."""
    cost_usd = cost.COST_ENGAGEMENT
    get_budget().check(cost_usd)
    if get_config().dry_run:
        return {"dry_run": True, "would_retweet": tweet_id}
    raw = await asyncio.to_thread(api_posts.retweet, get_client(), tweet_id)
    get_budget().record(cost_usd)
    return {"retweeted": True, "id": tweet_id, "raw": raw, "estimated_cost_usd": cost_usd}


@mcp.tool()
@handle_x_errors
async def x_unretweet(tweet_id: str) -> dict[str, Any]:
    """Undo a retweet. Cost ≈ $0.015."""
    cost_usd = cost.COST_ENGAGEMENT
    get_budget().check(cost_usd)
    if get_config().dry_run:
        return {"dry_run": True, "would_unretweet": tweet_id}
    raw = await asyncio.to_thread(api_posts.unretweet, get_client(), tweet_id)
    get_budget().record(cost_usd)
    return {"unretweeted": True, "id": tweet_id, "raw": raw, "estimated_cost_usd": cost_usd}


@mcp.tool()
@handle_x_errors
async def x_get_tweet(tweet_id: str) -> dict[str, Any]:
    """Look up a single tweet by ID (any author). Cost ≈ $0.005 (standard read)."""
    cost_usd = cost.COST_STANDARD_READ
    get_budget().check(cost_usd)
    raw = await asyncio.to_thread(api_posts.get_tweet, get_client(), tweet_id)
    get_budget().record(cost_usd)
    return {**trim_tweet(raw), "estimated_cost_usd": cost_usd}
