"""Revision history tools."""
from __future__ import annotations

import asyncio
from typing import Any

from ..api import files as files_api
from ..api import revisions as rev_api
from ..normalize import (
    clamp,
    default_export_mime,
    is_google_native,
    is_text_like,
    paginated,
    trim_revision,
)
from ._registry import get_service, handle_drive_errors, mcp


MAX_INLINE_BYTES = 1_000_000


@mcp.tool()
@handle_drive_errors
async def drive_list_revisions(
    file_id: str, max_results: int = 50, cursor: str | None = None
) -> dict[str, Any]:
    """List historical revisions of a file (chronological, oldest first)."""
    n = clamp(max_results, 1, 200)
    data = await asyncio.to_thread(
        rev_api.list_revisions,
        get_service(),
        file_id=file_id,
        page_size=n,
        page_token=cursor,
    )
    revs = data.get("revisions") or []
    return paginated(
        data, (trim_revision(r) for r in revs), item_key="revisions",
        extra={"file_id": file_id},
    )


@mcp.tool()
@handle_drive_errors
async def drive_get_revision(
    file_id: str, revision_id: str, export_mime: str | None = None
) -> dict[str, Any]:
    """Read the content of a specific historical revision as text.

    Same MIME logic as `drive_get_content`: Google-native files require an
    `export_mime` (or accept the default — markdown for Docs, CSV for Sheets,
    plain text for Slides). Binary revisions are rejected; download via
    `drive_export_file` if you need the bytes.
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
                    f"file {file_id} is Google native ({mime}); pass export_mime "
                    f"= text/markdown / text/csv / text/plain to read as text"
                )
            }
        # The Drive API does not support exporting an arbitrary historical
        # revision of a Google native file directly — only the head revision
        # can be exported. For native files we therefore export the head and
        # surface the limitation to the caller.
        return {
            "error": (
                "Drive does not support exporting historical revisions of "
                "Google-native files directly. Use drive_get_content for the "
                "current revision, or drive_export_file to download a binary "
                "snapshot of head."
            )
        }

    if is_text_like(mime):
        raw = await asyncio.to_thread(
            rev_api.download_revision,
            svc,
            file_id=file_id,
            revision_id=revision_id,
        )
        text = raw.decode("utf-8", errors="replace")
        truncated = len(text.encode("utf-8")) > MAX_INLINE_BYTES
        if truncated:
            text = text[:MAX_INLINE_BYTES]
        return {
            "id": file_id,
            "revision_id": revision_id,
            "name": name,
            "mimeType": mime,
            "content": text,
            "truncated": truncated,
        }

    return {
        "error": f"file {file_id} is binary ({mime}); revision read only supports text-like MIME types in v1"
    }
