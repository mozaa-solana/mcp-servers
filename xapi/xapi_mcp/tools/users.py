"""User-related tools: lookup, follow/unfollow, block/unblock.

Follow/unfollow take the *target* user's id. The authenticated user
(token holder) is the actor — Cách 1 model.
"""
from __future__ import annotations

import asyncio
from typing import Any

from .. import cost
from ..api import users as api_users
from ..normalize import trim_user
from ._registry import get_budget, get_client, get_config, handle_x_errors, mcp


async def _resolve_user_id(handle_or_id: str) -> str:
    """Accept either ``"123456"`` or ``"@alice"`` / ``"alice"`` and return the numeric id.

    Costs a standard read on the username path; free if you pass an id."""
    h = handle_or_id.strip().lstrip("@")
    if h.isdigit():
        return h
    raw = await asyncio.to_thread(api_users.get_by_username, get_client(), h)
    uid = getattr(raw, "id", None) or (raw.get("id") if isinstance(raw, dict) else None)
    if not uid:
        raise ValueError(f"could not resolve username: {handle_or_id}")
    return str(uid)


@mcp.tool()
@handle_x_errors
async def x_get_user(handle_or_id: str) -> dict[str, Any]:
    """Look up a user by ``@handle`` or numeric id.
    Cost ≈ $0.005 (standard read)."""
    cost_usd = cost.COST_STANDARD_READ
    get_budget().check(cost_usd)
    h = handle_or_id.strip().lstrip("@")
    if h.isdigit():
        raw = await asyncio.to_thread(api_users.get_by_id, get_client(), h)
    else:
        raw = await asyncio.to_thread(api_users.get_by_username, get_client(), h)
    get_budget().record(cost_usd)
    return {**trim_user(raw), "estimated_cost_usd": cost_usd}


@mcp.tool()
@handle_x_errors
async def x_follow_user(handle_or_id: str) -> dict[str, Any]:
    """Follow a user as the authenticated user. Pass ``@handle`` or numeric id.
    Cost ≈ $0.015 + a username lookup if needed."""
    cost_usd = cost.COST_ENGAGEMENT
    get_budget().check(cost_usd)
    if get_config().dry_run:
        return {"dry_run": True, "would_follow": handle_or_id}
    target_id = await _resolve_user_id(handle_or_id)
    raw = await asyncio.to_thread(api_users.follow, get_client(), target_id)
    get_budget().record(cost_usd)
    return {"followed": True, "target_id": target_id, "raw": raw, "estimated_cost_usd": cost_usd}


@mcp.tool()
@handle_x_errors
async def x_unfollow_user(handle_or_id: str) -> dict[str, Any]:
    """Unfollow a user. Pass ``@handle`` or numeric id. Cost ≈ $0.015."""
    cost_usd = cost.COST_ENGAGEMENT
    get_budget().check(cost_usd)
    if get_config().dry_run:
        return {"dry_run": True, "would_unfollow": handle_or_id}
    target_id = await _resolve_user_id(handle_or_id)
    raw = await asyncio.to_thread(api_users.unfollow, get_client(), target_id)
    get_budget().record(cost_usd)
    return {"unfollowed": True, "target_id": target_id, "raw": raw, "estimated_cost_usd": cost_usd}


@mcp.tool()
@handle_x_errors
async def x_block_user(handle_or_id: str) -> dict[str, Any]:
    """Block a user. Pass ``@handle`` or numeric id. Cost ≈ $0.015."""
    cost_usd = cost.COST_ENGAGEMENT
    get_budget().check(cost_usd)
    if get_config().dry_run:
        return {"dry_run": True, "would_block": handle_or_id}
    target_id = await _resolve_user_id(handle_or_id)
    raw = await asyncio.to_thread(api_users.block, get_client(), target_id)
    get_budget().record(cost_usd)
    return {"blocked": True, "target_id": target_id, "raw": raw, "estimated_cost_usd": cost_usd}


@mcp.tool()
@handle_x_errors
async def x_unblock_user(handle_or_id: str) -> dict[str, Any]:
    """Unblock a user. Pass ``@handle`` or numeric id. Cost ≈ $0.015."""
    cost_usd = cost.COST_ENGAGEMENT
    get_budget().check(cost_usd)
    if get_config().dry_run:
        return {"dry_run": True, "would_unblock": handle_or_id}
    target_id = await _resolve_user_id(handle_or_id)
    raw = await asyncio.to_thread(api_users.unblock, get_client(), target_id)
    get_budget().record(cost_usd)
    return {"unblocked": True, "target_id": target_id, "raw": raw, "estimated_cost_usd": cost_usd}
