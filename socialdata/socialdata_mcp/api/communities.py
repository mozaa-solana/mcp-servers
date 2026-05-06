"""Twitter Communities endpoints."""
from __future__ import annotations

from typing import Any

from ..config import Config
from ..http import request_json


async def get_community(config: Config, *, community_id: str) -> dict[str, Any]:
    """`GET /twitter/community/{community_id}`."""
    return await request_json(config, "GET", f"/twitter/community/{community_id}")


async def get_community_tweets(
    config: Config,
    *,
    community_id: str,
    sort: str = "Latest",
    cursor: str | None = None,
) -> dict[str, Any]:
    """`GET /twitter/community/{community_id}/tweets`."""
    params: dict[str, Any] = {"type": sort}
    if cursor:
        params["cursor"] = cursor
    return await request_json(
        config, "GET", f"/twitter/community/{community_id}/tweets", params=params
    )


async def get_community_members(
    config: Config, *, community_id: str, cursor: str | None = None
) -> dict[str, Any]:
    """`GET /twitter/community/{community_id}/members`."""
    params = {"cursor": cursor} if cursor else None
    return await request_json(
        config, "GET", f"/twitter/community/{community_id}/members", params=params
    )


async def search_community(
    config: Config,
    *,
    community_id: str,
    query: str,
    sort: str = "Latest",
    cursor: str | None = None,
) -> dict[str, Any]:
    """`GET /twitter/community/{community_id}/search`."""
    params: dict[str, Any] = {"query": query, "type": sort}
    if cursor:
        params["cursor"] = cursor
    return await request_json(
        config, "GET", f"/twitter/community/{community_id}/search", params=params
    )
