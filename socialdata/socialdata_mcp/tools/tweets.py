"""Tweet-resource MCP tools."""
from __future__ import annotations

from typing import Any

from ..api import tweets as api
from ..normalize import clamp, extract_items, paginated, trim_tweet, trim_user
from ._registry import get_config, mcp


def _validate_tweet_id(tweet_id: str) -> str | None:
    s = str(tweet_id).strip()
    return s if s.isdigit() else None


@mcp.tool()
async def twitter_tweet(tweet_id: str) -> dict[str, Any]:
    """Fetch a single tweet by numeric id.

    Endpoint: ``GET /twitter/tweets/{id}``.
    """
    tid = _validate_tweet_id(tweet_id)
    if tid is None:
        return {"error": "tweet_id must be a numeric string"}
    data = await api.get_tweet(get_config(), tweet_id=tid)
    return trim_tweet(data)


@mcp.tool()
async def twitter_tweets_lookup(ids: list[str]) -> dict[str, Any]:
    """Bulk tweet fetch by numeric ids. Max 100 ids per call.

    Endpoint: ``POST /twitter/tweets-by-ids``.
    """
    if not isinstance(ids, list) or not ids:
        return {"error": "ids must be a non-empty list"}
    if len(ids) > 100:
        return {"error": "max 100 ids per request"}
    bad = [i for i in ids if not str(i).strip().isdigit()]
    if bad:
        return {"error": f"non-numeric ids rejected: {bad[:5]}"}
    data = await api.get_tweets_by_ids(get_config(), ids=ids)
    tweets = extract_items(data, "tweets", "data")
    return {"count": len(tweets), "tweets": [trim_tweet(t) for t in tweets]}


@mcp.tool()
async def twitter_tweet_comments(
    tweet_id: str, max_results: int = 20, cursor: str | None = None
) -> dict[str, Any]:
    """Replies to a top-level tweet.

    Endpoint: ``GET /twitter/tweets/{id}/comments``.
    """
    tid = _validate_tweet_id(tweet_id)
    if tid is None:
        return {"error": "tweet_id must be a numeric string"}
    n = clamp(max_results, 1, 50)
    data = await api.get_tweet_comments(get_config(), tweet_id=tid, cursor=cursor)
    tweets = extract_items(data, "tweets", "data")[:n]
    return paginated(data, (trim_tweet(t) for t in tweets), item_key="tweets")


@mcp.tool()
async def twitter_tweet_quotes(
    tweet_id: str, max_results: int = 20, cursor: str | None = None
) -> dict[str, Any]:
    """Quote-tweets of a given tweet.

    Endpoint: ``GET /twitter/tweets/{id}/quotes``.
    """
    tid = _validate_tweet_id(tweet_id)
    if tid is None:
        return {"error": "tweet_id must be a numeric string"}
    n = clamp(max_results, 1, 50)
    data = await api.get_tweet_quotes(get_config(), tweet_id=tid, cursor=cursor)
    tweets = extract_items(data, "tweets", "data")[:n]
    return paginated(data, (trim_tweet(t) for t in tweets), item_key="tweets")


@mcp.tool()
async def twitter_tweet_retweeters(
    tweet_id: str, max_results: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    """Users who retweeted a given tweet.

    Endpoint: ``GET /twitter/tweets/{id}/retweeted_by``.
    """
    tid = _validate_tweet_id(tweet_id)
    if tid is None:
        return {"error": "tweet_id must be a numeric string"}
    n = clamp(max_results, 1, 100)
    data = await api.get_tweet_retweeters(get_config(), tweet_id=tid, cursor=cursor)
    users = extract_items(data, "users", "data")[:n]
    return paginated(data, (trim_user(u) for u in users), item_key="users")


@mcp.tool()
async def twitter_tweet_thread(
    thread_id: str, max_results: int = 30, cursor: str | None = None
) -> dict[str, Any]:
    """Conversation chain (~30 posts/page) authored as a thread.

    Endpoint: ``GET /twitter/thread/{thread_id}``.
    """
    tid = _validate_tweet_id(thread_id)
    if tid is None:
        return {"error": "thread_id must be a numeric string"}
    n = clamp(max_results, 1, 100)
    data = await api.get_tweet_thread(get_config(), thread_id=tid, cursor=cursor)
    tweets = extract_items(data, "tweets", "data")[:n]
    return paginated(data, (trim_tweet(t) for t in tweets), item_key="tweets")


@mcp.tool()
async def twitter_tweet_article(article_id: str) -> dict[str, Any]:
    """Article-attached tweet metadata + content.

    Endpoint: ``GET /twitter/article/{article_id}``.
    """
    aid = _validate_tweet_id(article_id)
    if aid is None:
        return {"error": "article_id must be a numeric string"}
    data = await api.get_tweet_article(get_config(), article_id=aid)
    trimmed = trim_tweet(data)
    if isinstance(data, dict) and "article" in data:
        trimmed["article"] = data["article"]
    return trimmed
