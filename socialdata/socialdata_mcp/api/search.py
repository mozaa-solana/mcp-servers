"""Search endpoints."""
from __future__ import annotations

from typing import Any

from ..config import Config
from ..http import request_json


async def search_tweets(
    config: Config,
    *,
    query: str,
    sort: str = "Latest",
    cursor: str | None = None,
) -> dict[str, Any]:
    """`GET /twitter/search` — full-text recent tweet search."""
    params: dict[str, Any] = {"query": query, "type": sort}
    if cursor:
        params["cursor"] = cursor
    return await request_json(config, "GET", "/twitter/search", params=params)
