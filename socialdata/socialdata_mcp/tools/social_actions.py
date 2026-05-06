"""Social-action verification MCP tools."""
from __future__ import annotations

from typing import Any

from ..api import social_actions as api
from ._registry import get_config, mcp


@mcp.tool()
async def twitter_verify_following(
    source_user_id: str, target_user_id: str
) -> dict[str, Any]:
    """Confirm whether ``source_user_id`` follows ``target_user_id``.

    Endpoint: ``GET /twitter/user/{source}/following/{target}``.
    """
    return await api.verify_following(
        get_config(), source_user_id=source_user_id, target_user_id=target_user_id
    )


@mcp.tool()
async def twitter_verify_retweeted(tweet_id: str, user_id: str) -> dict[str, Any]:
    """Verify a user retweeted a given tweet.

    Endpoint: ``GET /twitter/tweets/{tweet_id}/retweeted_by/{user_id}``.
    """
    return await api.verify_retweeted(get_config(), tweet_id=tweet_id, user_id=user_id)


@mcp.tool()
async def twitter_verify_commented(tweet_id: str, user_id: str) -> dict[str, Any]:
    """Verify a user commented (replied) on a given tweet.

    Endpoint: ``GET /twitter/tweets/{tweet_id}/commented_by/{user_id}``.
    """
    return await api.verify_commented(get_config(), tweet_id=tweet_id, user_id=user_id)
