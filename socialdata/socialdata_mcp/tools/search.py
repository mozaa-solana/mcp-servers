"""Search tools."""
from __future__ import annotations

from typing import Any

from ..api import search as api
from ..normalize import clamp, extract_items, paginated, trim_tweet
from ._registry import get_config, mcp


def _normalize_sort(sort: str) -> str:
    return "Top" if str(sort).lower() == "top" else "Latest"


@mcp.tool()
async def twitter_search(
    query: str,
    sort: str = "Latest",
    max_results: int = 20,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Search recent tweets matching `query`.

    Args:
        query: Twitter search query. Operators: ``from:user``, ``since:YYYY-MM-DD``,
               ``until:YYYY-MM-DD``, ``lang:en``, ``min_faves:N``, exact phrase quoting,
               ``-exclude``.
        sort: ``Latest`` (default — best for breaking news) or ``Top`` (engagement-ranked).
        max_results: 1–50 trimmed tweets to return from the page (default 20).
        cursor: Pagination cursor from previous ``next_cursor`` response.
    """
    n = clamp(max_results, 1, 50)
    sort_norm = _normalize_sort(sort)
    data = await api.search_tweets(get_config(), query=query, sort=sort_norm, cursor=cursor)
    tweets = extract_items(data, "tweets", "data")[:n]
    return paginated(
        data,
        (trim_tweet(t) for t in tweets),
        item_key="tweets",
        extra={"query": query, "sort": sort_norm},
    )
