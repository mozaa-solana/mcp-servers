"""Twitter Lists endpoints."""
from __future__ import annotations

from typing import Any

from ..config import Config
from ..http import request_json


async def get_list(config: Config, *, list_id: str) -> dict[str, Any]:
    """`GET /twitter/lists/show?id={list_id}`."""
    return await request_json(
        config, "GET", "/twitter/lists/show", params={"id": list_id}
    )


async def get_list_members(
    config: Config, *, list_id: str, cursor: str | None = None
) -> dict[str, Any]:
    """`GET /twitter/lists/members?list_id={list_id}`."""
    params: dict[str, Any] = {"list_id": list_id}
    if cursor:
        params["cursor"] = cursor
    return await request_json(config, "GET", "/twitter/lists/members", params=params)


async def get_list_tweets(
    config: Config, *, list_id: str, cursor: str | None = None
) -> dict[str, Any]:
    """`GET /twitter/list/{list_id}/tweets`."""
    params = {"cursor": cursor} if cursor else None
    return await request_json(
        config, "GET", f"/twitter/list/{list_id}/tweets", params=params
    )
