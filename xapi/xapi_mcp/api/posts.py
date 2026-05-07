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


def get_tweet(client: XClient, tweet_id: str) -> dict[str, Any]:
    """Single tweet lookup — useful for verifying engagement actions."""
    resp = client.v2.get_tweet(
        tweet_id,
        tweet_fields=["created_at", "author_id", "public_metrics", "lang",
                      "conversation_id", "in_reply_to_user_id"],
    )
    return resp.data or {}
