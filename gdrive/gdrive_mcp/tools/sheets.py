"""Google Sheets MCP tools (12).

Range strings use **A1 notation**: ``Sheet1!A1:B10`` (col-letter + row-number),
``'My Sheet'!A:B`` (whole columns), ``Sheet1!A:A`` (single column). Wrap sheet
names containing spaces in single quotes.

Resolve a `spreadsheet_id` by searching Drive (`drive_search` /
`drive_list_files`) — it is the same string as the file id.
"""
from __future__ import annotations

import asyncio
from typing import Any

from ..api import sheets as api
from ..normalize import trim_file, trim_spreadsheet
from ..safety import assert_in_working_folder
from ._registry import get_config, get_service, get_sheets_service, mcp


async def _check_safety(spreadsheet_id: str) -> None:
    """Apply the working-folder rail using the Drive client (sheets writes
    happen *inside* a spreadsheet, but the spreadsheet itself is a Drive file).
    """
    cfg = get_config()
    if cfg.working_folder_id:
        await asyncio.to_thread(
            assert_in_working_folder,
            get_service(),
            cfg.working_folder_id,
            spreadsheet_id,
        )


# --------------------------------------------------------------------------
# Read (3)
# --------------------------------------------------------------------------


@mcp.tool()
async def sheets_get_metadata(spreadsheet_id: str) -> dict[str, Any]:
    """Get spreadsheet metadata: title, locale, time zone, list of tabs
    (with sheet ids, titles, dimensions).

    Use this **first** when working with a new spreadsheet — agents need the
    sheet (tab) titles to build A1 ranges.
    """
    data = await asyncio.to_thread(
        api.get_spreadsheet, get_sheets_service(), spreadsheet_id=spreadsheet_id
    )
    return trim_spreadsheet(data)


@mcp.tool()
async def sheets_get_values(
    spreadsheet_id: str,
    range: str,
    value_render: str = "FORMATTED_VALUE",
    major_dimension: str = "ROWS",
) -> dict[str, Any]:
    """Read a cell range as a 2-D list.

    Args:
        range: A1 notation. Example: ``Sheet1!A1:C10`` or ``'My Sheet'!A:B``.
        value_render: ``FORMATTED_VALUE`` (default — what users see),
            ``UNFORMATTED_VALUE`` (raw values, dates as serial numbers),
            ``FORMULA`` (formulas instead of computed values).
        major_dimension: ``ROWS`` (default — values[r][c]) or ``COLUMNS``.
    """
    data = await asyncio.to_thread(
        api.get_values,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        range_=range,
        value_render=value_render,
        major_dim=major_dimension,
    )
    return {
        "spreadsheet_id": spreadsheet_id,
        "range": data.get("range"),
        "major_dimension": data.get("majorDimension"),
        "values": data.get("values") or [],
    }


@mcp.tool()
async def sheets_batch_get_values(
    spreadsheet_id: str,
    ranges: list[str],
    value_render: str = "FORMATTED_VALUE",
    major_dimension: str = "ROWS",
) -> dict[str, Any]:
    """Read multiple ranges in one call. Cheaper than N `sheets_get_values`."""
    if not ranges:
        return {"error": "ranges must be a non-empty list"}
    data = await asyncio.to_thread(
        api.batch_get_values,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        ranges=ranges,
        value_render=value_render,
        major_dim=major_dimension,
    )
    out = []
    for vr in data.get("valueRanges") or []:
        out.append(
            {
                "range": vr.get("range"),
                "major_dimension": vr.get("majorDimension"),
                "values": vr.get("values") or [],
            }
        )
    return {"spreadsheet_id": spreadsheet_id, "ranges": out}


# --------------------------------------------------------------------------
# Write — values (4)
# --------------------------------------------------------------------------


@mcp.tool()
async def sheets_update_values(
    spreadsheet_id: str,
    range: str,
    values: list[list[Any]],
    value_input: str = "USER_ENTERED",
) -> dict[str, Any]:
    """**Overwrite** cells in a range with the given 2-D values.

    `value_input`:
      - ``USER_ENTERED`` (default) — values are parsed as if a user typed them
        (formulas, dates, numbers auto-detected).
      - ``RAW`` — values stored literally (no parsing).
    """
    if not isinstance(values, list):
        return {"error": "values must be a 2-D list (list of rows)"}
    await _check_safety(spreadsheet_id)
    data = await asyncio.to_thread(
        api.update_values,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        range_=range,
        values=values,
        value_input=value_input,
    )
    return {
        "spreadsheet_id": spreadsheet_id,
        "updated_range": data.get("updatedRange"),
        "updated_rows": data.get("updatedRows"),
        "updated_columns": data.get("updatedColumns"),
        "updated_cells": data.get("updatedCells"),
    }


@mcp.tool()
async def sheets_append_values(
    spreadsheet_id: str,
    range: str,
    values: list[list[Any]],
    value_input: str = "USER_ENTERED",
) -> dict[str, Any]:
    """Append rows after the last row of data in `range`.

    Drive scans `range` to find the last non-empty row, then writes below it.
    Use this for log-style additions; use `sheets_update_values` to overwrite
    a specific range.
    """
    if not isinstance(values, list):
        return {"error": "values must be a 2-D list (list of rows)"}
    await _check_safety(spreadsheet_id)
    data = await asyncio.to_thread(
        api.append_values,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        range_=range,
        values=values,
        value_input=value_input,
    )
    updates = data.get("updates") or {}
    return {
        "spreadsheet_id": spreadsheet_id,
        "updated_range": updates.get("updatedRange"),
        "updated_rows": updates.get("updatedRows"),
        "updated_cells": updates.get("updatedCells"),
    }


@mcp.tool()
async def sheets_clear_values(spreadsheet_id: str, range: str) -> dict[str, Any]:
    """Clear (empty) cells in a range. Formulas referencing those cells will
    recompute as empty. Sheet structure (rows/cols) unchanged.
    """
    await _check_safety(spreadsheet_id)
    data = await asyncio.to_thread(
        api.clear_values, get_sheets_service(), spreadsheet_id=spreadsheet_id, range_=range
    )
    return {
        "spreadsheet_id": spreadsheet_id,
        "cleared_range": data.get("clearedRange"),
    }


@mcp.tool()
async def sheets_batch_update_values(
    spreadsheet_id: str,
    data: list[dict[str, Any]],
    value_input: str = "USER_ENTERED",
) -> dict[str, Any]:
    """Multi-range overwrite in a single call.

    `data` is a list of ``{"range": "Sheet1!A1:B2", "values": [[...], ...]}``.
    """
    if not isinstance(data, list) or not data:
        return {"error": "data must be a non-empty list of {range, values} entries"}
    await _check_safety(spreadsheet_id)
    resp = await asyncio.to_thread(
        api.batch_update_values,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        data=data,
        value_input=value_input,
    )
    return {
        "spreadsheet_id": spreadsheet_id,
        "total_updated_rows": resp.get("totalUpdatedRows"),
        "total_updated_cells": resp.get("totalUpdatedCells"),
        "responses": [
            {
                "updated_range": r.get("updatedRange"),
                "updated_cells": r.get("updatedCells"),
            }
            for r in resp.get("responses") or []
        ],
    }


# --------------------------------------------------------------------------
# Write — structure (5)
# --------------------------------------------------------------------------


@mcp.tool()
async def sheets_create_spreadsheet(
    title: str, parent_id: str | None = None
) -> dict[str, Any]:
    """Create a new empty spreadsheet, optionally inside `parent_id` folder.

    On personal Gmail, this typically fails with a quota error (SA has 0
    quota). Use a Workspace folder / Shared Drive as the parent for reliable
    creation. See README → "Quota gotcha".
    """
    cfg = get_config()
    if parent_id:
        await asyncio.to_thread(
            assert_in_working_folder, get_service(), cfg.working_folder_id, parent_id
        )
    elif cfg.working_folder_id:
        return {
            "error": (
                "GDRIVE_WORKING_FOLDER_ID is set; parent_id is required to keep the "
                "new spreadsheet inside the safety boundary"
            )
        }
    data = await asyncio.to_thread(
        api.create_via_drive, get_service(), title=title, parent_id=parent_id
    )
    return trim_file(data)


@mcp.tool()
async def sheets_add_sheet(spreadsheet_id: str, title: str) -> dict[str, Any]:
    """Add a new tab to an existing spreadsheet."""
    await _check_safety(spreadsheet_id)
    resp = await asyncio.to_thread(
        api.batch_update_structure,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        requests=[{"addSheet": {"properties": {"title": title}}}],
    )
    props = resp["replies"][0]["addSheet"]["properties"]
    return {
        "spreadsheet_id": spreadsheet_id,
        "sheet_id": props.get("sheetId"),
        "title": props.get("title"),
        "index": props.get("index"),
    }


@mcp.tool()
async def sheets_delete_sheet(spreadsheet_id: str, sheet_id: int) -> dict[str, Any]:
    """Delete a tab. **Irreversible** — Drive does NOT keep deleted tabs in
    spreadsheet revision history reliably. Double-check before calling.
    """
    await _check_safety(spreadsheet_id)
    await asyncio.to_thread(
        api.batch_update_structure,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        requests=[{"deleteSheet": {"sheetId": int(sheet_id)}}],
    )
    return {"spreadsheet_id": spreadsheet_id, "deleted_sheet_id": int(sheet_id)}


@mcp.tool()
async def sheets_rename_sheet(
    spreadsheet_id: str, sheet_id: int, new_title: str
) -> dict[str, Any]:
    """Rename a tab."""
    await _check_safety(spreadsheet_id)
    await asyncio.to_thread(
        api.batch_update_structure,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        requests=[
            {
                "updateSheetProperties": {
                    "properties": {"sheetId": int(sheet_id), "title": new_title},
                    "fields": "title",
                }
            }
        ],
    )
    return {
        "spreadsheet_id": spreadsheet_id,
        "sheet_id": int(sheet_id),
        "title": new_title,
    }


@mcp.tool()
async def sheets_duplicate_sheet(
    spreadsheet_id: str, sheet_id: int, new_title: str | None = None
) -> dict[str, Any]:
    """Duplicate an existing tab. Defaults to "Copy of <orig_title>" when
    `new_title` is not given.
    """
    await _check_safety(spreadsheet_id)
    req: dict[str, Any] = {"duplicateSheet": {"sourceSheetId": int(sheet_id)}}
    if new_title:
        req["duplicateSheet"]["newSheetName"] = new_title
    resp = await asyncio.to_thread(
        api.batch_update_structure,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        requests=[req],
    )
    props = resp["replies"][0]["duplicateSheet"]["properties"]
    return {
        "spreadsheet_id": spreadsheet_id,
        "source_sheet_id": int(sheet_id),
        "sheet_id": props.get("sheetId"),
        "title": props.get("title"),
        "index": props.get("index"),
    }
