"""``files`` resource — list / get metadata / search / create folder / mutate metadata."""
from __future__ import annotations

from typing import Any


FILE_FIELDS = (
    "id,name,mimeType,size,modifiedTime,createdTime,parents,"
    "owners(emailAddress,displayName),trashed,webViewLink"
)
FILE_LIST_FIELDS = f"nextPageToken,files({FILE_FIELDS})"


# Common kwargs for queries that need to traverse Shared Drives.
_SHARED_DRIVE_KW = {
    "supportsAllDrives": True,
    "includeItemsFromAllDrives": True,
}


def list_files(
    service: Any,
    *,
    q: str | None = None,
    page_size: int = 100,
    page_token: str | None = None,
    order_by: str | None = None,
) -> dict[str, Any]:
    """``files.list`` — Drive search / listing entrypoint."""
    kwargs: dict[str, Any] = {
        "pageSize": page_size,
        "fields": FILE_LIST_FIELDS,
        **_SHARED_DRIVE_KW,
    }
    if q:
        kwargs["q"] = q
    if page_token:
        kwargs["pageToken"] = page_token
    if order_by:
        kwargs["orderBy"] = order_by
    return service.files().list(**kwargs).execute()


def get_metadata(service: Any, *, file_id: str) -> dict[str, Any]:
    """``files.get`` (metadata only)."""
    return (
        service.files()
        .get(fileId=file_id, fields=FILE_FIELDS, supportsAllDrives=True)
        .execute()
    )


def create_folder(
    service: Any, *, name: str, parent_id: str | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        body["parents"] = [parent_id]
    return (
        service.files()
        .create(body=body, fields=FILE_FIELDS, supportsAllDrives=True)
        .execute()
    )


def rename(service: Any, *, file_id: str, new_name: str) -> dict[str, Any]:
    return (
        service.files()
        .update(
            fileId=file_id,
            body={"name": new_name},
            fields=FILE_FIELDS,
            supportsAllDrives=True,
        )
        .execute()
    )


def move(
    service: Any, *, file_id: str, new_parent_id: str
) -> dict[str, Any]:
    """Atomically reparent a file: remove all current parents, add the new one."""
    current = (
        service.files()
        .get(fileId=file_id, fields="parents", supportsAllDrives=True)
        .execute()
    )
    old_parents = ",".join(current.get("parents") or [])
    return (
        service.files()
        .update(
            fileId=file_id,
            addParents=new_parent_id,
            removeParents=old_parents,
            fields=FILE_FIELDS,
            supportsAllDrives=True,
        )
        .execute()
    )


def trash(service: Any, *, file_id: str) -> dict[str, Any]:
    """Move to trash (recoverable for 30 days). Not a permanent delete."""
    return (
        service.files()
        .update(
            fileId=file_id,
            body={"trashed": True},
            fields=FILE_FIELDS,
            supportsAllDrives=True,
        )
        .execute()
    )
