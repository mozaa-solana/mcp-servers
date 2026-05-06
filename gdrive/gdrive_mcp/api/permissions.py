"""``permissions`` resource — read-only listing for v1.

Mutating permissions (share / unshare / change role) is intentionally deferred
to v2 because it changes the security boundary and warrants its own audit
plumbing.
"""
from __future__ import annotations

from typing import Any


PERMISSION_FIELDS = (
    "id,type,role,emailAddress,domain,displayName,deleted"
)
PERMISSION_LIST_FIELDS = f"nextPageToken,permissions({PERMISSION_FIELDS})"


def list_permissions(
    service: Any, *, file_id: str, page_token: str | None = None
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "fileId": file_id,
        "fields": PERMISSION_LIST_FIELDS,
        "supportsAllDrives": True,
    }
    if page_token:
        kwargs["pageToken"] = page_token
    return service.permissions().list(**kwargs).execute()
