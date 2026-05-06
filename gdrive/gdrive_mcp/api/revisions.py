"""``revisions`` resource — file version history."""
from __future__ import annotations

from typing import Any


REVISION_FIELDS = (
    "id,modifiedTime,size,keepForever,"
    "lastModifyingUser(emailAddress,displayName)"
)
REVISION_LIST_FIELDS = f"nextPageToken,revisions({REVISION_FIELDS})"


def list_revisions(
    service: Any, *, file_id: str, page_token: str | None = None, page_size: int = 100
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "fileId": file_id,
        "pageSize": page_size,
        "fields": REVISION_LIST_FIELDS,
    }
    if page_token:
        kwargs["pageToken"] = page_token
    return service.revisions().list(**kwargs).execute()


def get_revision_metadata(
    service: Any, *, file_id: str, revision_id: str
) -> dict[str, Any]:
    return (
        service.revisions()
        .get(fileId=file_id, revisionId=revision_id, fields=REVISION_FIELDS)
        .execute()
    )


def download_revision(
    service: Any, *, file_id: str, revision_id: str
) -> bytes:
    """Download the bytes of a specific historical revision."""
    return (
        service.revisions()
        .get_media(fileId=file_id, revisionId=revision_id)
        .execute()
    )
