"""Per-resource verbs for /users endpoints. Sync — wrap in to_thread."""
from __future__ import annotations

from typing import Any

from ..x_client import XClient


def get_by_username(client: XClient, username: str) -> dict[str, Any]:
    resp = client.v2.get_user(
        username=username.lstrip("@"),
        user_fields=["description", "verified", "public_metrics", "created_at"],
    )
    return resp.data or {}


def get_by_id(client: XClient, user_id: str) -> dict[str, Any]:
    resp = client.v2.get_user(
        id=user_id,
        user_fields=["description", "verified", "public_metrics", "created_at"],
    )
    return resp.data or {}


def follow(client: XClient, target_user_id: str) -> dict[str, Any]:
    resp = client.v2.follow_user(target_user_id)
    return resp.data or {}


def unfollow(client: XClient, target_user_id: str) -> dict[str, Any]:
    resp = client.v2.unfollow_user(target_user_id)
    return resp.data or {}


def mute(client: XClient, target_user_id: str) -> dict[str, Any]:
    resp = client.v2.mute(target_user_id)
    return resp.data or {}


def unmute(client: XClient, target_user_id: str) -> dict[str, Any]:
    resp = client.v2.unmute(target_user_id)
    return resp.data or {}


def get_followers(
    client: XClient, user_id: str, max_results: int = 100, cursor: str | None = None
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "id": user_id,
        "max_results": max(1, min(max_results, 1000)),
        "user_fields": ["description", "verified", "public_metrics"],
    }
    if cursor:
        kwargs["pagination_token"] = cursor
    resp = client.v2.get_users_followers(**kwargs)
    items = list(resp.data or [])
    next_token = (resp.meta or {}).get("next_token")
    return {"items": items, "next_cursor": next_token}


def get_following(
    client: XClient, user_id: str, max_results: int = 100, cursor: str | None = None
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "id": user_id,
        "max_results": max(1, min(max_results, 1000)),
        "user_fields": ["description", "verified", "public_metrics"],
    }
    if cursor:
        kwargs["pagination_token"] = cursor
    resp = client.v2.get_users_following(**kwargs)
    items = list(resp.data or [])
    next_token = (resp.meta or {}).get("next_token")
    return {"items": items, "next_cursor": next_token}


def block(client: XClient, target_user_id: str) -> dict[str, Any]:
    resp = client.v2.block(target_user_id)
    return resp.data or {}


def unblock(client: XClient, target_user_id: str) -> dict[str, Any]:
    resp = client.v2.unblock(target_user_id)
    return resp.data or {}
