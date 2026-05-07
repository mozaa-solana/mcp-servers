"""Per-resource verbs for /tweets endpoints. Sync — wrap in to_thread."""
from __future__ import annotations

from typing import Any

from ..x_client import XClient


def create(
    client: XClient,
    text: str,
    *,
    reply_to_tweet_id: str | None = None,
    quote_tweet_id: str | None = None,
    media_ids: list[str] | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"text": text}
    if reply_to_tweet_id:
        kwargs["in_reply_to_tweet_id"] = reply_to_tweet_id
    if quote_tweet_id:
        kwargs["quote_tweet_id"] = quote_tweet_id
    if media_ids:
        kwargs["media_ids"] = media_ids
    resp = client.v2.create_tweet(**kwargs)
    return resp.data or {}


def delete(client: XClient, tweet_id: str) -> dict[str, Any]:
    resp = client.v2.delete_tweet(tweet_id)
    return resp.data or {}


def like(client: XClient, tweet_id: str) -> dict[str, Any]:
    resp = client.v2.like(tweet_id)
    return resp.data or {}


def unlike(client: XClient, tweet_id: str) -> dict[str, Any]:
    resp = client.v2.unlike(tweet_id)
    return resp.data or {}


def retweet(client: XClient, tweet_id: str) -> dict[str, Any]:
    resp = client.v2.retweet(tweet_id)
    return resp.data or {}


def unretweet(client: XClient, tweet_id: str) -> dict[str, Any]:
    resp = client.v2.unretweet(tweet_id)
    return resp.data or {}


def pin_tweet(client: XClient, tweet_id: str) -> dict[str, Any]:
    """Pin a tweet to the authenticated user's profile.

    Newer tweepy versions expose ``client.pin_tweet``. Older ones don't —
    fall back to a raw v2 request in that case."""
    fn = getattr(client.v2, "pin_tweet", None)
    if fn is not None:
        resp = fn(tweet_id)
        return getattr(resp, "data", None) or {}
    me = client.v2.get_me()
    me_id = me.data.id
    resp = client.v2.request(  # type: ignore[attr-defined]
        "POST", f"/2/users/{me_id}/pinned_tweets", json={"tweet_id": tweet_id},
    )
    return resp.json().get("data", {}) if hasattr(resp, "json") else {}


def unpin_tweet(client: XClient, tweet_id: str) -> dict[str, Any]:
    fn = getattr(client.v2, "unpin_tweet", None)
    if fn is not None:
        resp = fn(tweet_id)
        return getattr(resp, "data", None) or {}
    me = client.v2.get_me()
    me_id = me.data.id
    resp = client.v2.request(  # type: ignore[attr-defined]
        "DELETE", f"/2/users/{me_id}/pinned_tweets/{tweet_id}",
    )
    return resp.json().get("data", {}) if hasattr(resp, "json") else {}


def get_user_tweets(
    client: XClient, user_id: str, max_results: int = 10
) -> dict[str, Any]:
    """List a user's recent tweets. Returns ``{items, next_cursor}``."""
    resp = client.v2.get_users_tweets(
        id=user_id,
        max_results=max(5, min(max_results, 100)),
        tweet_fields=["created_at", "public_metrics", "lang",
                      "conversation_id", "in_reply_to_user_id"],
    )
    items = list(resp.data or [])
    next_token = (resp.meta or {}).get("next_token")
    return {"items": items, "next_cursor": next_token}


def get_tweet(client: XClient, tweet_id: str) -> dict[str, Any]:
    """Single tweet lookup — useful for verifying engagement actions."""
    resp = client.v2.get_tweet(
        tweet_id,
        tweet_fields=["created_at", "author_id", "public_metrics", "lang",
                      "conversation_id", "in_reply_to_user_id"],
    )
    return resp.data or {}
