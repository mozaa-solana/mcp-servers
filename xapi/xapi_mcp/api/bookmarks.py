"""v2 bookmarks endpoints — owned writes/reads, cheap tier."""
from __future__ import annotations

from typing import Any

from ..x_client import XClient


def add(client: XClient, tweet_id: str) -> dict[str, Any]:
    resp = client.v2.bookmark(tweet_id)
    return resp.data or {}


def remove(client: XClient, tweet_id: str) -> dict[str, Any]:
    resp = client.v2.remove_bookmark(tweet_id)
    return resp.data or {}


def list_(client: XClient, max_results: int = 10) -> dict[str, Any]:
    resp = client.v2.get_bookmarks(
        max_results=max(5, min(max_results, 100)),
        tweet_fields=["created_at", "public_metrics", "lang", "author_id"],
    )
    items = list(resp.data or [])
    next_token = (resp.meta or {}).get("next_token")
    return {"items": items, "next_cursor": next_token}
