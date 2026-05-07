"""Pure helpers to trim X API responses to LLM-friendly shape.

Tweepy returns ``Response`` objects with ``.data`` (Pydantic-ish) and
``.includes`` blocks. We flatten + trim to keep tokens out of the agent
context.
"""
from __future__ import annotations

from typing import Any

# What we keep from a tweet object — drop noisy stuff like edit history,
# context_annotations, possibly_sensitive flags that LLMs rarely need.
TWEET_FIELDS = ("id", "text", "created_at", "author_id", "conversation_id",
                "in_reply_to_user_id", "lang", "public_metrics")

USER_FIELDS = ("id", "name", "username", "description", "verified",
               "public_metrics", "created_at")


def _to_dict(obj: Any) -> dict[str, Any]:
    """Tweepy v4 returns ``ResultSet`` items that already behave as dicts;
    older shapes need ``.data`` extraction. Be defensive."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "data") and isinstance(obj.data, dict):
        return obj.data
    if hasattr(obj, "data"):
        return _to_dict(obj.data)
    # tweepy.Tweet / tweepy.User have a __dict__ with a ``data`` key
    if hasattr(obj, "__dict__"):
        d = obj.__dict__.get("data", obj.__dict__)
        if isinstance(d, dict):
            return d
    return {}


def trim_tweet(raw: Any) -> dict[str, Any]:
    d = _to_dict(raw)
    return {k: d[k] for k in TWEET_FIELDS if k in d}


def trim_user(raw: Any) -> dict[str, Any]:
    d = _to_dict(raw)
    return {k: d[k] for k in USER_FIELDS if k in d}


def paginated(items: list[Any], next_token: str | None, trim_fn) -> dict[str, Any]:
    """Uniform list envelope: ``{count, items[], next_cursor}``.

    Pass ``next_cursor`` back as ``cursor=`` to walk pages."""
    trimmed = [trim_fn(i) for i in items]
    return {
        "count": len(trimmed),
        "items": trimmed,
        "next_cursor": next_token,
    }
