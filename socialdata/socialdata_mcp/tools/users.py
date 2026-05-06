"""User-resource MCP tools."""
from __future__ import annotations

from typing import Any

from ..api import users as api
from ..normalize import clamp, extract_items, paginated, trim_tweet, trim_user
from ._registry import get_config, mcp

USERS_KEY = ("users", "data")
TWEETS_KEY = ("tweets", "data")


def _validate_ids(ids: list[Any]) -> dict[str, Any] | None:
    if not isinstance(ids, list) or not ids:
        return {"error": "ids must be a non-empty list"}
    if len(ids) > 100:
        return {"error": "max 100 ids per request"}
    return None


# --- Profile ---------------------------------------------------------------


@mcp.tool()
async def twitter_user_info(handle_or_id: str) -> dict[str, Any]:
    """Profile lookup. `handle_or_id` accepts a screen name (no @) or numeric user id.

    Endpoint: ``GET /twitter/user/{handle_or_id}``.
    """
    data = await api.get_user(get_config(), handle_or_id=handle_or_id)
    return trim_user(data)


@mcp.tool()
async def twitter_users_lookup(ids: list[str]) -> dict[str, Any]:
    """Bulk profile lookup by numeric user id. Max 100 ids.

    Endpoint: ``POST /twitter/users-by-id``.
    """
    if (err := _validate_ids(ids)) is not None:
        return err
    data = await api.get_users_by_ids(get_config(), ids=ids)
    users = extract_items(data, *USERS_KEY)
    return {"count": len(users), "users": [trim_user(u) for u in users]}


@mcp.tool()
async def twitter_user_extended_bio(screen_name: str) -> dict[str, Any]:
    """Extended biography (rich-text blocks, entities) when available.

    Endpoint: ``GET /twitter/user/{username}/extended-bio``.
    """
    return await api.get_user_extended_bio(get_config(), screen_name=screen_name)


# --- Timelines -------------------------------------------------------------


@mcp.tool()
async def twitter_user_tweets(
    user_id: str,
    include_replies: bool = False,
    max_results: int = 20,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Recent tweets posted by a user (numeric id required).

    Endpoint: ``GET /twitter/user/{user_id}/tweets`` (or ``…/tweets-and-replies``).
    """
    n = clamp(max_results, 1, 50)
    data = await api.get_user_tweets(
        get_config(), user_id=user_id, include_replies=include_replies, cursor=cursor
    )
    tweets = extract_items(data, *TWEETS_KEY)[:n]
    return paginated(
        data, (trim_tweet(t) for t in tweets), item_key="tweets",
        extra={"user_id": user_id, "include_replies": include_replies},
    )


@mcp.tool()
async def twitter_user_mentions(
    screen_name: str, max_results: int = 20, cursor: str | None = None
) -> dict[str, Any]:
    """Tweets mentioning the given user.

    Endpoint: ``GET /twitter/user/{username}/mentions``.
    """
    n = clamp(max_results, 1, 50)
    data = await api.get_user_mentions(get_config(), screen_name=screen_name, cursor=cursor)
    tweets = extract_items(data, *TWEETS_KEY)[:n]
    return paginated(data, (trim_tweet(t) for t in tweets), item_key="tweets")


@mcp.tool()
async def twitter_user_highlights(
    user_id: str, max_results: int = 20, cursor: str | None = None
) -> dict[str, Any]:
    """Highlighted (pinned-on-profile) tweets for a user.

    Endpoint: ``GET /twitter/user/{user_id}/highlights``.
    """
    n = clamp(max_results, 1, 50)
    data = await api.get_user_highlights(get_config(), user_id=user_id, cursor=cursor)
    tweets = extract_items(data, *TWEETS_KEY)[:n]
    return paginated(data, (trim_tweet(t) for t in tweets), item_key="tweets")


# --- Social graph ----------------------------------------------------------


@mcp.tool()
async def twitter_user_followers(
    user_id: str,
    verified_only: bool = False,
    max_results: int = 20,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Followers of a user (most recent first). Set ``verified_only=True`` for verified
    followers only.

    Endpoints: ``GET /twitter/followers/list`` or ``…/verified-followers``.
    """
    n = clamp(max_results, 1, 100)
    cfg = get_config()
    data = (
        await api.get_user_verified_followers(cfg, user_id=user_id, cursor=cursor)
        if verified_only
        else await api.get_user_followers(cfg, user_id=user_id, cursor=cursor)
    )
    users = extract_items(data, *USERS_KEY)[:n]
    return paginated(data, (trim_user(u) for u in users), item_key="users")


@mcp.tool()
async def twitter_user_followings(
    user_id: str, max_results: int = 20, cursor: str | None = None
) -> dict[str, Any]:
    """Accounts the given user follows.

    Endpoint: ``GET /twitter/friends/list``.
    """
    n = clamp(max_results, 1, 100)
    data = await api.get_user_followings(get_config(), user_id=user_id, cursor=cursor)
    users = extract_items(data, *USERS_KEY)[:n]
    return paginated(data, (trim_user(u) for u in users), item_key="users")


@mcp.tool()
async def twitter_user_similar(
    user_id: str, max_results: int = 20, cursor: str | None = None
) -> dict[str, Any]:
    """Profiles X considers similar to the given user.

    Endpoint: ``GET /twitter/user/{user_id}/similar``.
    """
    n = clamp(max_results, 1, 50)
    data = await api.get_user_similar(get_config(), user_id=user_id, cursor=cursor)
    users = extract_items(data, *USERS_KEY)[:n]
    return paginated(data, (trim_user(u) for u in users), item_key="users")


@mcp.tool()
async def twitter_user_affiliates(
    user_id: str, max_results: int = 20, cursor: str | None = None
) -> dict[str, Any]:
    """Org-affiliated accounts (gold-checkmark profiles only).

    Endpoint: ``GET /twitter/user/{user_id}/affiliates``.
    """
    n = clamp(max_results, 1, 100)
    data = await api.get_user_affiliates(get_config(), user_id=user_id, cursor=cursor)
    users = extract_items(data, *USERS_KEY)[:n]
    return paginated(data, (trim_user(u) for u in users), item_key="users")


@mcp.tool()
async def twitter_user_lists(
    user_id: str, max_results: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    """Twitter Lists owned/subscribed-to by the user. Returns raw list metadata.

    Endpoint: ``GET /twitter/user/{user_id}/lists``.
    """
    n = clamp(max_results, 1, 100)
    data = await api.get_user_lists(get_config(), user_id=user_id, cursor=cursor)
    lists = extract_items(data, "lists", "data")[:n]
    return paginated(data, lists, item_key="lists")
