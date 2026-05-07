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


def block(client: XClient, target_user_id: str) -> dict[str, Any]:
    resp = client.v2.block(target_user_id)
    return resp.data or {}


def unblock(client: XClient, target_user_id: str) -> dict[str, Any]:
    resp = client.v2.unblock(target_user_id)
    return resp.data or {}
