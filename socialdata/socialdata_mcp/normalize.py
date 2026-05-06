"""Pure normalization helpers — drop noisy upstream fields, keep what an LLM needs.

Functions in this module are deterministic and side-effect free; tests cover
field fall-backs (``id_str`` vs ``id``, ``full_text`` vs ``text``, etc.).
"""
from __future__ import annotations

from typing import Any, Iterable


def trim_user(u: dict[str, Any] | None) -> dict[str, Any]:
    """Compact representation of a user profile."""
    u = u or {}
    screen_name = u.get("screen_name")
    return {
        "id": u.get("id_str") or u.get("id"),
        "screen_name": screen_name,
        "name": u.get("name"),
        "description": u.get("description"),
        "verified": u.get("verified") or u.get("blue_verified"),
        "followers_count": u.get("followers_count"),
        "friends_count": u.get("friends_count") or u.get("following_count"),
        "statuses_count": u.get("statuses_count") or u.get("tweet_count"),
        "created_at": u.get("created_at") or u.get("user_created_at"),
        "url": f"https://x.com/{screen_name}" if screen_name else None,
    }


def trim_tweet(tw: dict[str, Any] | None) -> dict[str, Any]:
    """Compact representation of a tweet."""
    tw = tw or {}
    user = tw.get("user") or {}
    tweet_id = tw.get("id_str") or tw.get("id")
    screen_name = user.get("screen_name")
    return {
        "id": tweet_id,
        "created_at": tw.get("tweet_created_at") or tw.get("created_at"),
        "text": tw.get("full_text") or tw.get("text"),
        "lang": tw.get("lang"),
        "retweet_count": tw.get("retweet_count"),
        "favorite_count": tw.get("favorite_count"),
        "reply_count": tw.get("reply_count"),
        "quote_count": tw.get("quote_count"),
        "view_count": tw.get("views_count") or tw.get("view_count"),
        "url": (
            f"https://x.com/{screen_name}/status/{tweet_id}"
            if screen_name and tweet_id
            else None
        ),
        "author": {
            "screen_name": screen_name,
            "name": user.get("name"),
            "verified": user.get("verified") or user.get("blue_verified"),
            "followers_count": user.get("followers_count"),
        },
        "is_retweet": bool(tw.get("retweeted_status_result") or tw.get("retweeted_status")),
        "is_quote": bool(tw.get("quoted_status_result") or tw.get("is_quote_status")),
    }


def clamp(n: Any, lo: int, hi: int) -> int:
    """Coerce to int and clamp into ``[lo, hi]``."""
    try:
        v = int(n)
    except (TypeError, ValueError):
        v = lo
    return max(lo, min(v, hi))


def extract_items(data: dict[str, Any], *keys: str) -> list[dict[str, Any]]:
    """Pull the first list-valued key from *keys*; tolerate dict-shaped fallbacks."""
    for k in keys:
        v = data.get(k)
        if isinstance(v, list):
            return v
    return []


def paginated(
    data: dict[str, Any],
    items: Iterable[dict[str, Any]],
    *,
    item_key: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap a page of normalized *items* with cursor + count metadata."""
    items_list = list(items)
    out: dict[str, Any] = {
        "count": len(items_list),
        item_key: items_list,
        "next_cursor": data.get("next_cursor"),
    }
    if extra:
        out.update(extra)
    return out
