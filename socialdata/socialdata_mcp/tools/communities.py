"""Twitter Communities MCP tools."""
from __future__ import annotations

from typing import Any

from ..api import communities as api
from ..normalize import clamp, extract_items, paginated, trim_tweet, trim_user
from ._registry import get_config, mcp


def _normalize_sort(sort: str) -> str:
    return "Top" if str(sort).lower() == "top" else "Latest"


@mcp.tool()
async def twitter_community_info(community_id: str) -> dict[str, Any]:
    """Community metadata (name, description, member count).

    Endpoint: ``GET /twitter/community/{community_id}``.
    """
    return await api.get_community(get_config(), community_id=community_id)


@mcp.tool()
async def twitter_community_tweets(
    community_id: str,
    sort: str = "Latest",
    max_results: int = 20,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Tweets posted in a community timeline. Pinned posts repeat across pages.

    Endpoint: ``GET /twitter/community/{community_id}/tweets``.
    """
    n = clamp(max_results, 1, 50)
    sort_norm = _normalize_sort(sort)
    data = await api.get_community_tweets(
        get_config(), community_id=community_id, sort=sort_norm, cursor=cursor
    )
    tweets = extract_items(data, "tweets", "data")[:n]
    return paginated(
        data, (trim_tweet(t) for t in tweets), item_key="tweets",
        extra={"community_id": community_id, "sort": sort_norm},
    )


@mcp.tool()
async def twitter_community_members(
    community_id: str, max_results: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    """Members of a community.

    Endpoint: ``GET /twitter/community/{community_id}/members``.
    """
    n = clamp(max_results, 1, 100)
    data = await api.get_community_members(
        get_config(), community_id=community_id, cursor=cursor
    )
    users = extract_items(data, "users", "data")[:n]
    return paginated(data, (trim_user(u) for u in users), item_key="users")


@mcp.tool()
async def twitter_community_search(
    community_id: str,
    query: str,
    sort: str = "Latest",
    max_results: int = 20,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Search tweets within a community.

    Endpoint: ``GET /twitter/community/{community_id}/search``.
    """
    n = clamp(max_results, 1, 50)
    sort_norm = _normalize_sort(sort)
    data = await api.search_community(
        get_config(),
        community_id=community_id,
        query=query,
        sort=sort_norm,
        cursor=cursor,
    )
    tweets = extract_items(data, "tweets", "data")[:n]
    return paginated(
        data, (trim_tweet(t) for t in tweets), item_key="tweets",
        extra={"community_id": community_id, "query": query, "sort": sort_norm},
    )
