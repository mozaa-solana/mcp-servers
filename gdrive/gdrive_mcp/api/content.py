"""File content I/O — download / export / upload / update.

Google native files (Docs/Sheets/Slides) are *exported* (server-side
conversion) rather than downloaded. Regular files are downloaded as bytes.
"""
from __future__ import annotations

from typing import Any

from googleapiclient.http import MediaFileUpload, MediaInMemoryUpload

from .files import FILE_FIELDS


def download_bytes(service: Any, *, file_id: str) -> bytes:
    """``files.get`` with ``alt=media`` — raw bytes for non-Google files."""
    return service.files().get_media(fileId=file_id, supportsAllDrives=True).execute()


def export_bytes(service: Any, *, file_id: str, mime_type: str) -> bytes:
    """``files.export`` — server-side conversion of Google native files."""
    return service.files().export_media(fileId=file_id, mimeType=mime_type).execute()


def upload_file(
    service: Any,
    *,
    local_path: str,
    name: str | None = None,
    parent_id: str | None = None,
    mime_type: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"name": name} if name else {}
    if not body.get("name"):
        import os

        body["name"] = os.path.basename(local_path)
    if parent_id:
        body["parents"] = [parent_id]
    media = MediaFileUpload(local_path, mimetype=mime_type, resumable=False)
    return (
        service.files()
        .create(
            body=body, media_body=media, fields=FILE_FIELDS, supportsAllDrives=True
        )
        .execute()
    )


def create_text_file(
    service: Any,
    *,
    name: str,
    content: str,
    parent_id: str | None = None,
    mime_type: str = "text/plain",
) -> dict[str, Any]:
    body: dict[str, Any] = {"name": name}
    if parent_id:
        body["parents"] = [parent_id]
    media = MediaInMemoryUpload(content.encode("utf-8"), mimetype=mime_type)
    return (
        service.files()
        .create(
            body=body, media_body=media, fields=FILE_FIELDS, supportsAllDrives=True
        )
        .execute()
    )


def update_content(
    service: Any,
    *,
    file_id: str,
    content: str,
    mime_type: str = "text/plain",
) -> dict[str, Any]:
    media = MediaInMemoryUpload(content.encode("utf-8"), mimetype=mime_type)
    return (
        service.files()
        .update(
            fileId=file_id,
            media_body=media,
            fields=FILE_FIELDS,
            supportsAllDrives=True,
        )
        .execute()
    )
