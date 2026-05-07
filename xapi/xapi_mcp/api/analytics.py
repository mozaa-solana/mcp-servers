"""Per-tweet analytics endpoints (v2)."""
from __future__ import annotations

from typing import Any

from ..x_client import XClient


def get_liking_users(
    client: XClient, tweet_id: str, max_results: int = 100, cursor: str | None = None
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "id": tweet_id,
        "max_results": max(1, min(max_results, 100)),
        "user_fields": ["description", "verified", "public_metrics"],
    }
    if cursor:
        kwargs["pagination_token"] = cursor
    resp = client.v2.get_liking_users(**kwargs)
    items = list(resp.data or [])
    next_token = (resp.meta or {}).get("next_token")
    return {"items": items, "next_cursor": next_token}


def get_retweeters(
    client: XClient, tweet_id: str, max_results: int = 100, cursor: str | None = None
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "id": tweet_id,
        "max_results": max(1, min(max_results, 100)),
        "user_fields": ["description", "verified", "public_metrics"],
    }
    if cursor:
        kwargs["pagination_token"] = cursor
    resp = client.v2.get_retweeters(**kwargs)
    items = list(resp.data or [])
    next_token = (resp.meta or {}).get("next_token")
    return {"items": items, "next_cursor": next_token}


def get_quote_tweets(
    client: XClient, tweet_id: str, max_results: int = 10, cursor: str | None = None
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "id": tweet_id,
        "max_results": max(10, min(max_results, 100)),
        "tweet_fields": ["created_at", "public_metrics", "lang", "author_id",
                         "conversation_id"],
    }
    if cursor:
        kwargs["pagination_token"] = cursor
    resp = client.v2.get_quote_tweets(**kwargs)
    items = list(resp.data or [])
    next_token = (resp.meta or {}).get("next_token")
    return {"items": items, "next_cursor": next_token}


def get_tweet_with_metrics(client: XClient, tweet_id: str) -> dict[str, Any]:
    """Return a tweet INCLUDING ``non_public_metrics`` and ``organic_metrics``.

    These extra metric blocks are only returned for tweets authored by
    the authenticated user. For everyone else's tweets, only
    ``public_metrics`` is populated."""
    resp = client.v2.get_tweet(
        tweet_id,
        tweet_fields=[
            "created_at", "author_id", "public_metrics",
            "non_public_metrics", "organic_metrics",
            "lang", "conversation_id",
        ],
        user_auth=True,
    )
    return resp.data or {}
