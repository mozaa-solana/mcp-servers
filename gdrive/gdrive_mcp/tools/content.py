"""Content I/O tools — read, upload, create, update, export."""
from __future__ import annotations

import asyncio
import os
from typing import Any

from ..api import content as content_api
from ..api import files as files_api
from ..normalize import (
    default_export_mime,
    is_google_native,
    is_text_like,
    trim_file,
)
from ..safety import assert_in_working_folder
from ._registry import get_config, get_service, mcp


MAX_INLINE_BYTES = 1_000_000  # 1 MB cap on inline text returned to the LLM


def _decode(b: bytes) -> str:
    """Decode bytes as utf-8, falling back to latin-1 for binary-ish text."""
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("latin-1", errors="replace")


def _truncate(text: str) -> tuple[str, bool]:
    if len(text.encode("utf-8")) <= MAX_INLINE_BYTES:
        return text, False
    # rough cut to keep us near the byte limit
    return text[:MAX_INLINE_BYTES], True


# --------------------------------------------------------------------------
# Read
# --------------------------------------------------------------------------


@mcp.tool()
async def drive_get_content(
    file_id: str, export_mime: str | None = None
) -> dict[str, Any]:
    """Return file content as text.

    Behaviour by file type:
      - **Google Docs/Sheets/Slides/Drawings** → server-side export
        (defaults: Doc → markdown, Sheet → CSV, Slides → text, Drawing → PNG —
        binary case rejected; pass `export_mime` to override).
      - **text/\\***, JSON, YAML, etc. → downloaded and decoded as utf-8.
      - **Binary files** (PDF, images, zip, …) → rejected with a hint to use
        `drive_export_file` to save to disk instead.

    Output is capped at 1 MB; longer content is truncated with `truncated=true`.
    """
    svc = get_service()
    meta = await asyncio.to_thread(files_api.get_metadata, svc, file_id=file_id)
    mime = meta.get("mimeType")
    name = meta.get("name")

    if is_google_native(mime):
        target = export_mime or default_export_mime(mime)
        if not target or not target.startswith(("text/", "application/json")):
            return {
                "error": (
                    f"file {file_id} is a Google native ({mime}); pass export_mime "
                    f"= text/markdown / text/csv / text/plain to read as text, or "
                    f"use drive_export_file to save the binary export to disk"
                )
            }
        raw = await asyncio.to_thread(
            content_api.export_bytes, svc, file_id=file_id, mime_type=target
        )
        text, truncated = _truncate(_decode(raw))
        return {
            "id": file_id,
            "name": name,
            "mimeType": mime,
            "exported_as": target,
            "content": text,
            "truncated": truncated,
        }

    if is_text_like(mime):
        raw = await asyncio.to_thread(content_api.download_bytes, svc, file_id=file_id)
        text, truncated = _truncate(_decode(raw))
        return {
            "id": file_id,
            "name": name,
            "mimeType": mime,
            "content": text,
            "truncated": truncated,
        }

    return {
        "error": (
            f"file {file_id} is binary ({mime}); use drive_export_file to save "
            f"it to a local path"
        ),
        "mimeType": mime,
    }


@mcp.tool()
async def drive_export_file(
    file_id: str, export_mime: str, local_path: str
) -> dict[str, Any]:
    """Save a Google native file (or any binary) to a local path.

    For Google Docs use e.g. `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`,
    `text/markdown`. For Sheets: `text/csv`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
    """
    svc = get_service()
    meta = await asyncio.to_thread(files_api.get_metadata, svc, file_id=file_id)

    parent = os.path.dirname(os.path.abspath(local_path)) or "."
    if not os.path.isdir(parent):
        return {"error": f"parent directory does not exist: {parent}"}

    if is_google_native(meta.get("mimeType")):
        raw = await asyncio.to_thread(
            content_api.export_bytes, svc, file_id=file_id, mime_type=export_mime
        )
    else:
        raw = await asyncio.to_thread(content_api.download_bytes, svc, file_id=file_id)

    await asyncio.to_thread(_write_bytes, local_path, raw)
    return {
        "id": file_id,
        "name": meta.get("name"),
        "saved_to": os.path.abspath(local_path),
        "bytes_written": len(raw),
        "exported_as": export_mime if is_google_native(meta.get("mimeType")) else None,
    }


def _write_bytes(path: str, data: bytes) -> None:
    with open(path, "wb") as fh:
        fh.write(data)


# --------------------------------------------------------------------------
# Write
# --------------------------------------------------------------------------


@mcp.tool()
async def drive_upload_file(
    local_path: str,
    name: str | None = None,
    parent_id: str | None = None,
    mime_type: str | None = None,
) -> dict[str, Any]:
    """Upload a local file to Drive.

    `name` defaults to the basename of `local_path`. `mime_type` is auto-detected
    by googleapiclient if omitted. The destination parent must lie inside the
    working folder when the safety rail is enabled.
    """
    if not os.path.isfile(local_path):
        return {"error": f"local file not found: {local_path}"}

    svc = get_service()
    cfg = get_config()
    if parent_id:
        await asyncio.to_thread(
            assert_in_working_folder, svc, cfg.working_folder_id, parent_id
        )
    elif cfg.working_folder_id:
        return {
            "error": (
                "GDRIVE_WORKING_FOLDER_ID is set; parent_id is required to keep the "
                "uploaded file inside the safety boundary"
            )
        }

    data = await asyncio.to_thread(
        content_api.upload_file,
        svc,
        local_path=local_path,
        name=name,
        parent_id=parent_id,
        mime_type=mime_type,
    )
    return trim_file(data)


@mcp.tool()
async def drive_create_text_file(
    name: str,
    content: str,
    parent_id: str | None = None,
    mime_type: str = "text/plain",
) -> dict[str, Any]:
    """Create a new text/markdown/json file directly from the supplied content.

    Use `mime_type='text/markdown'` for `.md`, `'application/json'` for JSON,
    etc. For binary files use `drive_upload_file` instead.
    """
    svc = get_service()
    cfg = get_config()
    if parent_id:
        await asyncio.to_thread(
            assert_in_working_folder, svc, cfg.working_folder_id, parent_id
        )
    elif cfg.working_folder_id:
        return {
            "error": (
                "GDRIVE_WORKING_FOLDER_ID is set; parent_id is required to keep the "
                "new file inside the safety boundary"
            )
        }

    data = await asyncio.to_thread(
        content_api.create_text_file,
        svc,
        name=name,
        content=content,
        parent_id=parent_id,
        mime_type=mime_type,
    )
    return trim_file(data)


@mcp.tool()
async def drive_update_file_content(
    file_id: str, content: str, mime_type: str = "text/plain"
) -> dict[str, Any]:
    """Replace an existing file's content. Old content is **overwritten** —
    Drive keeps a revision in history (see `drive_list_revisions`)."""
    svc = get_service()
    cfg = get_config()
    await asyncio.to_thread(
        assert_in_working_folder, svc, cfg.working_folder_id, file_id
    )
    data = await asyncio.to_thread(
        content_api.update_content,
        svc,
        file_id=file_id,
        content=content,
        mime_type=mime_type,
    )
    return trim_file(data)
