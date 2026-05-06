"""User-resource endpoints (profiles, timelines, social graph)."""
from __future__ import annotations

from typing import Any, Iterable

from ..config import Config
from ..http import request_json


def _strip_at(handle: str) -> str:
    return handle.lstrip("@").strip()


async def get_user(config: Config, *, handle_or_id: str) -> dict[str, Any]:
    """`GET /twitter/user/{username_or_id}` — accepts username or numeric id."""
    return await request_json(config, "GET", f"/twitter/user/{_strip_at(handle_or_id)}")


async def get_users_by_ids(config: Config, *, ids: Iterable[Any]) -> dict[str, Any]:
    """`POST /twitter/users-by-id` — up to 100 ids per call."""
    return await request_json(
        config, "POST", "/twitter/users-by-id", json={"ids": [str(i) for i in ids]}
    )


async def get_user_followers(
    config: Config, *, user_id: str, cursor: str | None = None
) -> dict[str, Any]:
    """`GET /twitter/followers/list`."""
    params: dict[str, Any] = {"user_id": user_id}
    if cursor:
        params["cursor"] = cursor
    return await request_json(config, "GET", "/twitter/followers/list", params=params)


async def get_user_verified_followers(
    config: Config, *, user_id: str, cursor: str | None = None
) -> dict[str, Any]:
    """`GET /twitter/user/{user_id}/verified-followers`."""
    params = {"cursor": cursor} if cursor else None
    return await request_json(
        config, "GET", f"/twitter/user/{user_id}/verified-followers", params=params
    )


async def get_user_followings(
    config: Config, *, user_id: str, cursor: str | None = None
) -> dict[str, Any]:
    """`GET /twitter/friends/list`."""
    params: dict[str, Any] = {"user_id": user_id}
    if cursor:
        params["cursor"] = cursor
    return await request_json(config, "GET", "/twitter/friends/list", params=params)


async def get_user_tweets(
    config: Config,
    *,
    user_id: str,
    include_replies: bool = False,
    cursor: str | None = None,
) -> dict[str, Any]:
    """`GET /twitter/user/{user_id}/tweets[ -and-replies]`."""
    suffix = "tweets-and-replies" if include_replies else "tweets"
    params = {"cursor": cursor} if cursor else None
    return await request_json(
        config, "GET", f"/twitter/user/{user_id}/{suffix}", params=params
    )


async def get_user_mentions(
    config: Config, *, screen_name: str, cursor: str | None = None
) -> dict[str, Any]:
    """`GET /twitter/user/{username}/mentions`."""
    params = {"cursor": cursor} if cursor else None
    return await request_json(
        config, "GET", f"/twitter/user/{_strip_at(screen_name)}/mentions", params=params
    )


async def get_user_highlights(
    config: Config, *, user_id: str, cursor: str | None = None
) -> dict[str, Any]:
    """`GET /twitter/user/{user_id}/highlights`."""
    params = {"cursor": cursor} if cursor else None
    return await request_json(
        config, "GET", f"/twitter/user/{user_id}/highlights", params=params
    )


async def get_user_affiliates(
    config: Config, *, user_id: str, cursor: str | None = None
) -> dict[str, Any]:
    """`GET /twitter/user/{user_id}/affiliates`."""
    params = {"cursor": cursor} if cursor else None
    return await request_json(
        config, "GET", f"/twitter/user/{user_id}/affiliates", params=params
    )


async def get_user_lists(
    config: Config, *, user_id: str, cursor: str | None = None
) -> dict[str, Any]:
    """`GET /twitter/user/{user_id}/lists`."""
    params = {"cursor": cursor} if cursor else None
    return await request_json(
        config, "GET", f"/twitter/user/{user_id}/lists", params=params
    )


async def get_user_extended_bio(config: Config, *, screen_name: str) -> dict[str, Any]:
    """`GET /twitter/user/{username}/extended-bio`."""
    return await request_json(
        config, "GET", f"/twitter/user/{_strip_at(screen_name)}/extended-bio"
    )


async def get_user_similar(
    config: Config, *, user_id: str, cursor: str | None = None
) -> dict[str, Any]:
    """`GET /twitter/user/{user_id}/similar`."""
    params = {"cursor": cursor} if cursor else None
    return await request_json(
        config, "GET", f"/twitter/user/{user_id}/similar", params=params
    )
