"""Recent-search endpoint (v2)."""
from __future__ import annotations

from typing import Any

from ..x_client import XClient


def recent(
    client: XClient,
    query: str,
    *,
    max_results: int = 10,
    cursor: str | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "query": query,
        "max_results": max(10, min(max_results, 100)),
        "tweet_fields": ["created_at", "public_metrics", "lang",
                         "conversation_id", "author_id", "in_reply_to_user_id"],
    }
    if cursor:
        kwargs["next_token"] = cursor
    resp = client.v2.search_recent_tweets(**kwargs)
    items = list(resp.data or [])
    next_token = (resp.meta or {}).get("next_token")
    return {"items": items, "next_cursor": next_token}
