"""Permissions (read-only in v1)."""
from __future__ import annotations

import asyncio
from typing import Any

from ..api import permissions as perm_api
from ..normalize import paginated, trim_permission
from ._registry import get_service, handle_drive_errors, mcp


@mcp.tool()
@handle_drive_errors
async def drive_list_permissions(
    file_id: str, cursor: str | None = None
) -> dict[str, Any]:
    """List who has access to a file/folder (and at what role).

    Useful for debugging "the bot can't see file X" — verify the service
    account email shows up here with `role` >= reader.
    """
    data = await asyncio.to_thread(
        perm_api.list_permissions, get_service(), file_id=file_id, page_token=cursor
    )
    perms = data.get("permissions") or []
    return paginated(
        data,
        (trim_permission(p) for p in perms),
        item_key="permissions",
        extra={"file_id": file_id},
    )
