#!/usr/bin/env python3
"""
socialdata-mcp — MCP stdio server wrapping socialdata.tools REST API.

Exposes Twitter/X realtime tools to MCP-aware agents (Claude CLI,
opencode-go, goclaw bridge consumers).

Tools:
  twitter_search         — full-text recent tweet search
  twitter_user_tweets    — recent tweets from a user
  twitter_user_info      — profile lookup
  twitter_tweet          — fetch a single tweet by id

Auth: SOCIALDATA_API_KEY env var (required).
Transport: stdio.
Deps: mcp>=1.0, httpx.
"""
import os
import sys
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

API_KEY = os.environ.get("SOCIALDATA_API_KEY", "").strip()
if not API_KEY:
    print("error: SOCIALDATA_API_KEY env var required", file=sys.stderr)
    sys.exit(1)

BASE_URL = os.environ.get("SOCIALDATA_BASE_URL", "https://api.socialdata.tools").rstrip("/")
HTTP_TIMEOUT = float(os.environ.get("SOCIALDATA_TIMEOUT", "30"))

mcp = FastMCP("socialdata-twitter")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Accept": "application/json",
        },
    )


def _trim_tweet(tw: dict[str, Any]) -> dict[str, Any]:
    """Drop noisy fields, keep what a research agent needs."""
    user = tw.get("user") or {}
    return {
        "id": tw.get("id_str") or tw.get("id"),
        "created_at": tw.get("tweet_created_at") or tw.get("created_at"),
        "text": tw.get("full_text") or tw.get("text"),
        "lang": tw.get("lang"),
        "retweet_count": tw.get("retweet_count"),
        "favorite_count": tw.get("favorite_count"),
        "reply_count": tw.get("reply_count"),
        "quote_count": tw.get("quote_count"),
        "view_count": tw.get("views_count") or tw.get("view_count"),
        "url": (
            f"https://x.com/{user.get('screen_name')}/status/{tw.get('id_str') or tw.get('id')}"
            if user.get("screen_name") and (tw.get("id_str") or tw.get("id"))
            else None
        ),
        "author": {
            "screen_name": user.get("screen_name"),
            "name": user.get("name"),
            "verified": user.get("verified") or user.get("blue_verified"),
            "followers_count": user.get("followers_count"),
        },
        "is_retweet": bool(tw.get("retweeted_status_result") or tw.get("retweeted_status")),
        "is_quote": bool(tw.get("quoted_status_result") or tw.get("is_quote_status")),
    }


@mcp.tool()
async def twitter_search(
    query: str,
    sort: str = "Latest",
    max_results: int = 20,
) -> dict[str, Any]:
    """Search recent tweets matching `query`.

    Args:
        query: Twitter search query. Supports operators: from:user, since:YYYY-MM-DD,
               until:YYYY-MM-DD, lang:en, min_faves:N, "exact phrase", -exclude.
        sort: "Latest" (recent first, default — best for breaking news) or "Top"
              (engagement-ranked).
        max_results: How many tweets to return (1-50). Default 20.

    Returns:
        {"count": N, "query": query, "sort": sort, "tweets": [trimmed_tweet, ...]}
        Each tweet has: id, created_at (UTC), text, lang, engagement counts,
        url (canonical x.com permalink), author info, is_retweet, is_quote.
    """
    n = max(1, min(int(max_results), 50))
    sort = "Top" if sort.lower() == "top" else "Latest"
    async with _client() as c:
        r = await c.get(f"{BASE_URL}/twitter/search", params={"query": query, "type": sort})
        r.raise_for_status()
        data = r.json()
    tweets = data.get("tweets") or data.get("data") or []
    return {
        "count": min(len(tweets), n),
        "query": query,
        "sort": sort,
        "tweets": [_trim_tweet(t) for t in tweets[:n]],
    }


@mcp.tool()
async def twitter_user_tweets(screen_name: str, max_results: int = 20) -> dict[str, Any]:
    """Fetch a user's most recent tweets by their X/Twitter handle (no leading @).

    Args:
        screen_name: e.g. "elonmusk" — without the @.
        max_results: 1-50. Default 20.
    """
    n = max(1, min(int(max_results), 50))
    sn = screen_name.lstrip("@")
    async with _client() as c:
        r = await c.get(f"{BASE_URL}/twitter/user/{sn}/tweets")
        r.raise_for_status()
        data = r.json()
    tweets = data.get("tweets") or data.get("data") or []
    return {
        "count": min(len(tweets), n),
        "screen_name": sn,
        "tweets": [_trim_tweet(t) for t in tweets[:n]],
    }


@mcp.tool()
async def twitter_user_info(screen_name: str) -> dict[str, Any]:
    """Fetch X/Twitter user profile info by handle (no leading @)."""
    sn = screen_name.lstrip("@")
    async with _client() as c:
        r = await c.get(f"{BASE_URL}/twitter/user/{sn}")
        r.raise_for_status()
        u = r.json()
    return {
        "screen_name": u.get("screen_name") or sn,
        "name": u.get("name"),
        "description": u.get("description"),
        "verified": u.get("verified") or u.get("blue_verified"),
        "followers_count": u.get("followers_count"),
        "friends_count": u.get("friends_count") or u.get("following_count"),
        "statuses_count": u.get("statuses_count") or u.get("tweet_count"),
        "created_at": u.get("created_at") or u.get("user_created_at"),
        "url": f"https://x.com/{u.get('screen_name') or sn}",
    }


@mcp.tool()
async def twitter_tweet(tweet_id: str) -> dict[str, Any]:
    """Fetch a single tweet by its numeric id (string)."""
    tid = str(tweet_id).strip()
    if not tid.isdigit():
        return {"error": "tweet_id must be a numeric string"}
    async with _client() as c:
        r = await c.get(f"{BASE_URL}/twitter/statuses/show/{tid}")
        r.raise_for_status()
        return _trim_tweet(r.json())


if __name__ == "__main__":
    mcp.run(transport="stdio")
