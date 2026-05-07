"""Owned-read endpoints — cheaper tier ($0.001 vs $0.005)."""
from __future__ import annotations

from typing import Any

from ..x_client import XClient


def get_me(client: XClient) -> dict[str, Any]:
    resp = client.v2.get_me(
        user_fields=["description", "verified", "public_metrics", "created_at"],
    )
    return resp.data or {}


def get_my_followers(
    client: XClient, max_results: int = 100, cursor: str | None = None
) -> dict[str, Any]:
    me = client.v2.get_me()
    me_id = me.data.id if me.data else None
    if me_id is None:
        return {"items": [], "next_cursor": None}
    from . import users as api_users
    return api_users.get_followers(client, me_id, max_results=max_results, cursor=cursor)


def get_my_following(
    client: XClient, max_results: int = 100, cursor: str | None = None
) -> dict[str, Any]:
    me = client.v2.get_me()
    me_id = me.data.id if me.data else None
    if me_id is None:
        return {"items": [], "next_cursor": None}
    from . import users as api_users
    return api_users.get_following(client, me_id, max_results=max_results, cursor=cursor)


def get_my_recent_posts(client: XClient, max_results: int = 10) -> dict[str, Any]:
    """List the authenticated user's recent tweets. Returns ``{items, next_cursor}``."""
    me = client.v2.get_me()
    if not me.data:
        return {"items": [], "next_cursor": None}
    me_id = me.data.id

    resp = client.v2.get_users_tweets(
        id=me_id,
        max_results=max(5, min(max_results, 100)),
        tweet_fields=["created_at", "public_metrics", "lang",
                      "conversation_id", "in_reply_to_user_id"],
    )
    items = list(resp.data or [])
    next_token = (resp.meta or {}).get("next_token")
    return {"items": items, "next_cursor": next_token}
