"""Files: list / search / metadata / folder tree / write metadata mutations."""
from __future__ import annotations

import asyncio
from typing import Any

from ..api import files as files_api
from ..normalize import clamp, is_folder, paginated, trim_file
from ..safety import assert_in_working_folder
from ._registry import get_config, get_service, mcp


def _escape(value: str) -> str:
    """Escape a literal for inclusion in a Drive query string."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


# --------------------------------------------------------------------------
# Read
# --------------------------------------------------------------------------


@mcp.tool()
async def drive_list_files(
    folder_id: str | None = None,
    name_contains: str | None = None,
    max_results: int = 50,
    cursor: str | None = None,
) -> dict[str, Any]:
    """List files. If `folder_id` is given, restrict to that folder's children;
    otherwise list everything visible to the service account.

    `name_contains` is convenience filter (case-insensitive). For more advanced
    filters use `drive_search` with full Drive query operators.
    """
    n = clamp(max_results, 1, 1000)
    parts = ["trashed = false"]
    if folder_id:
        parts.append(f"'{_escape(folder_id)}' in parents")
    if name_contains:
        parts.append(f"name contains '{_escape(name_contains)}'")
    q = " and ".join(parts)

    data = await asyncio.to_thread(
        files_api.list_files,
        get_service(),
        q=q,
        page_size=n,
        page_token=cursor,
        order_by="modifiedTime desc",
    )
    files = data.get("files") or []
    return paginated(data, (trim_file(f) for f in files), item_key="files")


@mcp.tool()
async def drive_search(
    query: str,
    max_results: int = 50,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Run a raw Drive query string (full operator support).

    Examples:
      - `name contains 'budget'`
      - `fullText contains 'roadmap'`
      - `mimeType = 'application/vnd.google-apps.spreadsheet'`
      - `modifiedTime > '2026-01-01T00:00:00'`

    The tool always appends `and trashed = false` for safety. Combine clauses
    with `and` / `or` and wrap text in single quotes.
    """
    n = clamp(max_results, 1, 1000)
    q = f"({query}) and trashed = false" if query else "trashed = false"
    data = await asyncio.to_thread(
        files_api.list_files,
        get_service(),
        q=q,
        page_size=n,
        page_token=cursor,
        order_by="modifiedTime desc",
    )
    files = data.get("files") or []
    return paginated(
        data, (trim_file(f) for f in files), item_key="files", extra={"query": query}
    )


@mcp.tool()
async def drive_get_metadata(file_id: str) -> dict[str, Any]:
    """Fetch metadata (name, mime, size, parents, owners, modified time) for a file."""
    data = await asyncio.to_thread(files_api.get_metadata, get_service(), file_id=file_id)
    return trim_file(data)


@mcp.tool()
async def drive_get_folder_tree(
    folder_id: str,
    max_depth: int = 3,
    max_files_per_level: int = 200,
) -> dict[str, Any]:
    """Recursively walk *folder_id* up to *max_depth* levels.

    Returns a flat list of `{depth, parent, ...trim_file}` entries (BFS order).
    Costs one API call per folder visited — keep `max_depth` modest on large
    trees.
    """
    depth = clamp(max_depth, 0, 10)
    per_level = clamp(max_files_per_level, 1, 1000)
    svc = get_service()

    out: list[dict[str, Any]] = []
    queue: list[tuple[str, int]] = [(folder_id, 0)]
    while queue:
        fid, lvl = queue.pop(0)
        if lvl >= depth:
            continue
        page = await asyncio.to_thread(
            files_api.list_files,
            svc,
            q=f"'{_escape(fid)}' in parents and trashed = false",
            page_size=per_level,
            order_by="folder, name",
        )
        for f in page.get("files") or []:
            entry = {"depth": lvl + 1, "parent": fid, **trim_file(f)}
            out.append(entry)
            if is_folder(f.get("mimeType")):
                queue.append((f["id"], lvl + 1))

    return {"count": len(out), "root": folder_id, "max_depth": depth, "entries": out}


# --------------------------------------------------------------------------
# Write
# --------------------------------------------------------------------------


@mcp.tool()
async def drive_create_folder(
    name: str, parent_id: str | None = None
) -> dict[str, Any]:
    """Create a new folder. `parent_id=None` → service account's root."""
    svc = get_service()
    cfg = get_config()
    if parent_id:
        await asyncio.to_thread(
            assert_in_working_folder, svc, cfg.working_folder_id, parent_id
        )
    data = await asyncio.to_thread(
        files_api.create_folder, svc, name=name, parent_id=parent_id
    )
    return trim_file(data)


@mcp.tool()
async def drive_rename_file(file_id: str, new_name: str) -> dict[str, Any]:
    """Rename a file or folder."""
    svc = get_service()
    cfg = get_config()
    await asyncio.to_thread(
        assert_in_working_folder, svc, cfg.working_folder_id, file_id
    )
    data = await asyncio.to_thread(
        files_api.rename, svc, file_id=file_id, new_name=new_name
    )
    return trim_file(data)


@mcp.tool()
async def drive_move_file(file_id: str, new_parent_id: str) -> dict[str, Any]:
    """Move *file_id* to *new_parent_id*. Both old and new locations must be
    inside the working folder when the safety rail is enabled."""
    svc = get_service()
    cfg = get_config()
    await asyncio.to_thread(
        assert_in_working_folder, svc, cfg.working_folder_id, file_id
    )
    await asyncio.to_thread(
        assert_in_working_folder, svc, cfg.working_folder_id, new_parent_id
    )
    data = await asyncio.to_thread(
        files_api.move, svc, file_id=file_id, new_parent_id=new_parent_id
    )
    return trim_file(data)


@mcp.tool()
async def drive_trash_file(file_id: str) -> dict[str, Any]:
    """Move a file to Trash. **Recoverable for 30 days via the Drive web UI** —
    this is NOT a permanent delete. Permanent deletion is intentionally not
    exposed in v1.
    """
    svc = get_service()
    cfg = get_config()
    await asyncio.to_thread(
        assert_in_working_folder, svc, cfg.working_folder_id, file_id
    )
    data = await asyncio.to_thread(files_api.trash, svc, file_id=file_id)
    return trim_file(data)


@mcp.tool()
async def drive_untrash_file(file_id: str) -> dict[str, Any]:
    """Restore a file from Trash. Pair with `drive_trash_file`."""
    svc = get_service()
    cfg = get_config()
    await asyncio.to_thread(
        assert_in_working_folder, svc, cfg.working_folder_id, file_id
    )
    data = await asyncio.to_thread(files_api.untrash, svc, file_id=file_id)
    return trim_file(data)


@mcp.tool()
async def drive_copy_file(
    file_id: str, new_name: str | None = None, parent_id: str | None = None
) -> dict[str, Any]:
    """Duplicate a file. Common pattern: "make a copy from this template".

    `new_name` defaults to "Copy of <orig>". `parent_id` defaults to the same
    folder as the source. The destination must lie inside the working folder
    when the safety rail is enabled.
    """
    svc = get_service()
    cfg = get_config()
    if parent_id:
        await asyncio.to_thread(
            assert_in_working_folder, svc, cfg.working_folder_id, parent_id
        )
    elif cfg.working_folder_id:
        # No explicit parent → would inherit source's parent. Verify the
        # source sits inside the rail (its parents will be inherited).
        await asyncio.to_thread(
            assert_in_working_folder, svc, cfg.working_folder_id, file_id
        )
    data = await asyncio.to_thread(
        files_api.copy_file, svc, file_id=file_id, name=new_name, parent_id=parent_id
    )
    return trim_file(data)
