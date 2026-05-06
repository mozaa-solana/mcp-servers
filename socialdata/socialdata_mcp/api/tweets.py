"""Tweet-resource endpoints."""
from __future__ import annotations

from typing import Any, Iterable

from ..config import Config
from ..http import request_json


async def get_tweet(config: Config, *, tweet_id: str) -> dict[str, Any]:
    """`GET /twitter/tweets/{id}`."""
    return await request_json(config, "GET", f"/twitter/tweets/{tweet_id}")


async def get_tweets_by_ids(config: Config, *, ids: Iterable[Any]) -> dict[str, Any]:
    """`POST /twitter/tweets-by-ids` — up to 100 ids per call."""
    return await request_json(
        config, "POST", "/twitter/tweets-by-ids", json={"ids": [str(i) for i in ids]}
    )


async def get_tweet_comments(
    config: Config, *, tweet_id: str, cursor: str | None = None
) -> dict[str, Any]:
    """`GET /twitter/tweets/{id}/comments`."""
    params = {"cursor": cursor} if cursor else None
    return await request_json(
        config, "GET", f"/twitter/tweets/{tweet_id}/comments", params=params
    )


async def get_tweet_quotes(
    config: Config, *, tweet_id: str, cursor: str | None = None
) -> dict[str, Any]:
    """`GET /twitter/tweets/{id}/quotes`."""
    params = {"cursor": cursor} if cursor else None
    return await request_json(
        config, "GET", f"/twitter/tweets/{tweet_id}/quotes", params=params
    )


async def get_tweet_retweeters(
    config: Config, *, tweet_id: str, cursor: str | None = None
) -> dict[str, Any]:
    """`GET /twitter/tweets/{id}/retweeted_by`."""
    params = {"cursor": cursor} if cursor else None
    return await request_json(
        config, "GET", f"/twitter/tweets/{tweet_id}/retweeted_by", params=params
    )


async def get_tweet_thread(
    config: Config, *, thread_id: str, cursor: str | None = None
) -> dict[str, Any]:
    """`GET /twitter/thread/{thread_id}`."""
    params = {"cursor": cursor} if cursor else None
    return await request_json(
        config, "GET", f"/twitter/thread/{thread_id}", params=params
    )


async def get_tweet_article(config: Config, *, article_id: str) -> dict[str, Any]:
    """`GET /twitter/article/{article_id}`."""
    return await request_json(config, "GET", f"/twitter/article/{article_id}")
