"""Twitter Lists MCP tools."""
from __future__ import annotations

from typing import Any

from ..api import lists as api
from ..normalize import clamp, extract_items, paginated, trim_tweet, trim_user
from ._registry import get_config, mcp


@mcp.tool()
async def twitter_list_info(list_id: str) -> dict[str, Any]:
    """Twitter List metadata (member/subscriber counts, owner).

    Endpoint: ``GET /twitter/lists/show?id={list_id}``.
    """
    return await api.get_list(get_config(), list_id=list_id)


@mcp.tool()
async def twitter_list_members(
    list_id: str, max_results: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    """Members of a Twitter List.

    Endpoint: ``GET /twitter/lists/members?list_id={list_id}``.
    """
    n = clamp(max_results, 1, 100)
    data = await api.get_list_members(get_config(), list_id=list_id, cursor=cursor)
    users = extract_items(data, "users", "data")[:n]
    return paginated(data, (trim_user(u) for u in users), item_key="users")


@mcp.tool()
async def twitter_list_tweets(
    list_id: str, max_results: int = 30, cursor: str | None = None
) -> dict[str, Any]:
    """Tweets posted by members of a Twitter List.

    Endpoint: ``GET /twitter/list/{list_id}/tweets``.
    """
    n = clamp(max_results, 1, 50)
    data = await api.get_list_tweets(get_config(), list_id=list_id, cursor=cursor)
    tweets = extract_items(data, "tweets", "data")[:n]
    return paginated(data, (trim_tweet(t) for t in tweets), item_key="tweets")
