"""v1.1 account-level updates (profile bio + image).

X has no v2 endpoints for these — must use the legacy API surface
through ``tweepy.API``. Free per X's pricing docs.
"""
from __future__ import annotations

from typing import Any

from ..x_client import XClient


def update_profile(
    client: XClient,
    *,
    name: str | None = None,
    description: str | None = None,
    location: str | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    """Update the authenticated user's profile fields. Pass only the ones
    you want to change — omitted fields are left untouched."""
    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if location is not None:
        kwargs["location"] = location
    if url is not None:
        kwargs["url"] = url
    user = client.v1.update_profile(**kwargs)
    # tweepy.API.update_profile returns a User object with ``_json`` dict.
    return getattr(user, "_json", None) or {"name": getattr(user, "name", None)}


def update_profile_image(client: XClient, local_path: str) -> dict[str, Any]:
    """Replace the avatar image. PNG/JPG/GIF, ≤ 700KB per X's limits."""
    user = client.v1.update_profile_image(filename=local_path)
    return getattr(user, "_json", None) or {}
