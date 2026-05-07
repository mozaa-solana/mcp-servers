"""Identity / health / shared-files tools."""
from __future__ import annotations

import asyncio
from typing import Any

from ..api import about as about_api
from ..api import drives as drives_api
from ..api import files as files_api
from ..normalize import clamp, paginated, trim_file
from ._registry import get_service, handle_drive_errors, mcp


@mcp.tool()
@handle_drive_errors
async def drive_about() -> dict[str, Any]:
    """Show the service-account identity and Drive storage quota.

    Use this first to confirm the MCP server can authenticate and that the
    service-account email matches what you shared folders to.
    """
    data = await asyncio.to_thread(about_api.get_about, get_service())
    user = data.get("user") or {}
    quota = data.get("storageQuota") or {}
    return {
        "service_account_email": user.get("emailAddress"),
        "name": user.get("displayName"),
        "quota": {
            "limit": int(quota["limit"]) if quota.get("limit") else None,
            "usage": int(quota["usage"]) if quota.get("usage") else None,
            "usage_in_drive": (
                int(quota["usageInDrive"]) if quota.get("usageInDrive") else None
            ),
        },
    }


@mcp.tool()
@handle_drive_errors
async def drive_list_shared_with_me(
    max_results: int = 50,
    cursor: str | None = None,
) -> dict[str, Any]:
    """List files explicitly shared *with* the service account.

    On a personal-Gmail setup this is the canonical "what can the bot see?"
    view — the SA only sees files/folders someone has shared to its email.
    """
    n = clamp(max_results, 1, 1000)
    data = await asyncio.to_thread(
        files_api.list_files,
        get_service(),
        q="sharedWithMe = true and trashed = false",
        page_size=n,
        page_token=cursor,
        order_by="modifiedTime desc",
    )
    files = data.get("files") or []
    return paginated(data, (trim_file(f) for f in files), item_key="files")


@mcp.tool()
@handle_drive_errors
async def drive_list_drives(
    max_results: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    """List Shared Drives the service account is a member of.

    Empty list is normal on personal Gmail (Shared Drives are a Workspace
    feature). Use this to discover drive ids whose quota the SA can write
    into — sidesteps the personal-Gmail quota gotcha.
    """
    n = clamp(max_results, 1, 100)
    data = await asyncio.to_thread(
        drives_api.list_drives, get_service(), page_size=n, page_token=cursor
    )
    drives = data.get("drives") or []
    trimmed = [
        {
            "id": d.get("id"),
            "name": d.get("name"),
            "created": d.get("createdTime"),
            "hidden": d.get("hidden", False),
        }
        for d in drives
    ]
    return paginated(data, trimmed, item_key="drives")
