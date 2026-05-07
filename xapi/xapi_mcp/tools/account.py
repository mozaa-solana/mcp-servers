"""Profile-management tools (bio, name, avatar)."""
from __future__ import annotations

import asyncio
import os
from typing import Any

from ..api import account as api_account
from ._registry import get_client, get_config, handle_x_errors, mcp


@mcp.tool()
@handle_x_errors
async def x_update_profile(
    name: str | None = None,
    description: str | None = None,
    location: str | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    """Update the authenticated user's profile.

    Pass only the fields you want to change — omitted fields are left
    untouched. Free per X's pricing (v1.1 endpoint).

    Args:
        name: Display name (≤ 50 chars).
        description: Bio (≤ 160 chars).
        location: Free-text location (≤ 30 chars).
        url: Profile URL (must include scheme).
    """
    if all(v is None for v in (name, description, location, url)):
        return {"error": "pass at least one field to update"}
    if get_config().dry_run:
        return {"dry_run": True, "would_update": {
            "name": name, "description": description,
            "location": location, "url": url,
        }}
    raw = await asyncio.to_thread(
        api_account.update_profile,
        get_client(),
        name=name, description=description, location=location, url=url,
    )
    return {"updated": True, "profile": raw, "estimated_cost_usd": 0.0}


@mcp.tool()
@handle_x_errors
async def x_update_profile_image(local_path: str) -> dict[str, Any]:
    """Replace the avatar image. PNG/JPG/GIF, ≤ 700KB. Free per X."""
    if not os.path.exists(local_path):
        return {"error": f"local file not found: {local_path}"}
    if get_config().dry_run:
        return {"dry_run": True, "would_upload": local_path}
    raw = await asyncio.to_thread(
        api_account.update_profile_image, get_client(), local_path
    )
    return {"updated": True, "profile": raw, "estimated_cost_usd": 0.0}
