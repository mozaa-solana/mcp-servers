"""``drives`` resource — Shared Drives discovery."""
from __future__ import annotations

from typing import Any


DRIVE_FIELDS = "id,name,createdTime,hidden,restrictions"
DRIVES_LIST_FIELDS = f"nextPageToken,drives({DRIVE_FIELDS})"


def list_drives(
    service: Any, *, page_size: int = 50, page_token: str | None = None
) -> dict[str, Any]:
    """``drives.list`` — Shared Drives the service account is a member of.

    Returns the empty list when the SA has no Shared Drive memberships
    (typical on personal Gmail). On Workspace, this is how you discover
    drives whose quota the SA can write into.
    """
    kwargs: dict[str, Any] = {"pageSize": page_size, "fields": DRIVES_LIST_FIELDS}
    if page_token:
        kwargs["pageToken"] = page_token
    return service.drives().list(**kwargs).execute()
