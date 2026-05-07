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
from ._registry import get_config, get_service, get_sheets_service, handle_drive_errors, mcp


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
@handle_drive_errors
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
@handle_drive_errors
async def sheets_get_values(
    spreadsheet_id: str,
    cell_range: str,
    value_render: str = "FORMATTED_VALUE",
    major_dimension: str = "ROWS",
) -> dict[str, Any]:
    """Read a cell range as a 2-D list.

    Args:
        cell_range: A1 notation. Example: ``Sheet1!A1:C10`` or ``'My Sheet'!A:B``.
        value_render: ``FORMATTED_VALUE`` (default — what users see),
            ``UNFORMATTED_VALUE`` (raw values, dates as serial numbers),
            ``FORMULA`` (formulas instead of computed values).
        major_dimension: ``ROWS`` (default — values[r][c]) or ``COLUMNS``.
    """
    data = await asyncio.to_thread(
        api.get_values,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        range_=cell_range,
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
@handle_drive_errors
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
@handle_drive_errors
async def sheets_update_values(
    spreadsheet_id: str,
    cell_range: str,
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
        range_=cell_range,
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
@handle_drive_errors
async def sheets_append_values(
    spreadsheet_id: str,
    cell_range: str,
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
        range_=cell_range,
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
@handle_drive_errors
async def sheets_clear_values(spreadsheet_id: str, cell_range: str) -> dict[str, Any]:
    """Clear (empty) cells in a range. Formulas referencing those cells will
    recompute as empty. Sheet structure (rows/cols) unchanged.
    """
    await _check_safety(spreadsheet_id)
    data = await asyncio.to_thread(
        api.clear_values, get_sheets_service(), spreadsheet_id=spreadsheet_id, range_=cell_range
    )
    return {
        "spreadsheet_id": spreadsheet_id,
        "cleared_range": data.get("clearedRange"),
    }


@mcp.tool()
@handle_drive_errors
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
@handle_drive_errors
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
@handle_drive_errors
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
@handle_drive_errors
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
@handle_drive_errors
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
@handle_drive_errors
async def sheets_find_replace(
    spreadsheet_id: str,
    find: str,
    replace: str,
    sheet_id: int | None = None,
    match_case: bool = False,
    match_entire_cell: bool = False,
) -> dict[str, Any]:
    """Find/replace text. Scope: a single tab (`sheet_id`) or all tabs (None).

    Returns the count of cells affected. Use `match_entire_cell=True` to
    require an exact match (avoids partial-string substitutions).
    """
    await _check_safety(spreadsheet_id)
    resp = await asyncio.to_thread(
        api.find_replace,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        find=find,
        replace=replace,
        sheet_id=sheet_id,
        match_case=match_case,
        match_entire_cell=match_entire_cell,
    )
    fr = (resp.get("replies") or [{}])[0].get("findReplace") or {}
    return {
        "spreadsheet_id": spreadsheet_id,
        "occurrences_changed": fr.get("occurrencesChanged", 0),
        "values_changed": fr.get("valuesChanged", 0),
        "rows_changed": fr.get("rowsChanged", 0),
        "sheets_changed": fr.get("sheetsChanged", 0),
    }


@mcp.tool()
@handle_drive_errors
async def sheets_insert_rows(
    spreadsheet_id: str, sheet_id: int, start_index: int, count: int = 1
) -> dict[str, Any]:
    """Insert *count* blank rows at row index *start_index* (0-based).

    Existing rows at *start_index* and below shift down. Different from
    `sheets_append_values` (which appends after the last row of data) and
    `sheets_clear_values` (which only empties cells).
    """
    if count < 1:
        return {"error": "count must be >= 1"}
    await _check_safety(spreadsheet_id)
    await asyncio.to_thread(
        api.insert_dimension,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        dimension="ROWS",
        start_index=start_index,
        count=count,
    )
    return {
        "spreadsheet_id": spreadsheet_id,
        "sheet_id": int(sheet_id),
        "inserted_rows": int(count),
        "at_index": int(start_index),
    }


@mcp.tool()
@handle_drive_errors
async def sheets_delete_rows(
    spreadsheet_id: str, sheet_id: int, start_index: int, count: int = 1
) -> dict[str, Any]:
    """Delete *count* rows starting at row index *start_index* (0-based).

    Removes the rows entirely (not just clears content). Rows below shift up.
    """
    if count < 1:
        return {"error": "count must be >= 1"}
    await _check_safety(spreadsheet_id)
    await asyncio.to_thread(
        api.delete_dimension,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        dimension="ROWS",
        start_index=start_index,
        count=count,
    )
    return {
        "spreadsheet_id": spreadsheet_id,
        "sheet_id": int(sheet_id),
        "deleted_rows": int(count),
        "at_index": int(start_index),
    }


@mcp.tool()
@handle_drive_errors
async def sheets_insert_cols(
    spreadsheet_id: str, sheet_id: int, start_index: int, count: int = 1
) -> dict[str, Any]:
    """Insert *count* blank columns at column index *start_index* (0-based).

    Column A = 0, B = 1, etc. Columns at *start_index* and right shift right.
    """
    if count < 1:
        return {"error": "count must be >= 1"}
    await _check_safety(spreadsheet_id)
    await asyncio.to_thread(
        api.insert_dimension,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        dimension="COLUMNS",
        start_index=start_index,
        count=count,
    )
    return {
        "spreadsheet_id": spreadsheet_id,
        "sheet_id": int(sheet_id),
        "inserted_cols": int(count),
        "at_index": int(start_index),
    }


@mcp.tool()
@handle_drive_errors
async def sheets_delete_cols(
    spreadsheet_id: str, sheet_id: int, start_index: int, count: int = 1
) -> dict[str, Any]:
    """Delete *count* columns starting at column index *start_index* (0-based)."""
    if count < 1:
        return {"error": "count must be >= 1"}
    await _check_safety(spreadsheet_id)
    await asyncio.to_thread(
        api.delete_dimension,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        dimension="COLUMNS",
        start_index=start_index,
        count=count,
    )
    return {
        "spreadsheet_id": spreadsheet_id,
        "sheet_id": int(sheet_id),
        "deleted_cols": int(count),
        "at_index": int(start_index),
    }


@mcp.tool()
@handle_drive_errors
async def sheets_sort_range(
    spreadsheet_id: str,
    sheet_id: int,
    start_row_index: int,
    end_row_index: int,
    start_column_index: int,
    end_column_index: int,
    sort_column_index: int,
    descending: bool = False,
) -> dict[str, Any]:
    """Sort a GridRange by one column.

    All indices are 0-based, end indices are *exclusive* (Drive convention).
    `sort_column_index` is the **absolute** column index in the sheet (not an
    offset within the range). Example: to sort A1:C10 by column B descending,
    pass start_row_index=0, end_row_index=10, start_column_index=0,
    end_column_index=3, sort_column_index=1, descending=True.
    """
    await _check_safety(spreadsheet_id)
    await asyncio.to_thread(
        api.sort_range,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        start_row_index=start_row_index,
        end_row_index=end_row_index,
        start_column_index=start_column_index,
        end_column_index=end_column_index,
        sort_column_index=sort_column_index,
        descending=descending,
    )
    return {
        "spreadsheet_id": spreadsheet_id,
        "sheet_id": int(sheet_id),
        "sorted_by_column": int(sort_column_index),
        "order": "DESCENDING" if descending else "ASCENDING",
    }


@mcp.tool()
@handle_drive_errors
async def sheets_copy_sheet_to_spreadsheet(
    source_spreadsheet_id: str,
    source_sheet_id: int,
    destination_spreadsheet_id: str,
) -> dict[str, Any]:
    """Copy a tab from one spreadsheet into a different spreadsheet.

    Source remains unchanged. Returns the new sheet's properties inside the
    destination. Safety rail applies to the **destination** (the spreadsheet
    being mutated) — source only needs read access.
    """
    cfg = get_config()
    if cfg.working_folder_id:
        await asyncio.to_thread(
            assert_in_working_folder,
            get_service(),
            cfg.working_folder_id,
            destination_spreadsheet_id,
        )
    resp = await asyncio.to_thread(
        api.copy_sheet_to,
        get_sheets_service(),
        source_spreadsheet_id=source_spreadsheet_id,
        source_sheet_id=source_sheet_id,
        destination_spreadsheet_id=destination_spreadsheet_id,
    )
    return {
        "source_spreadsheet_id": source_spreadsheet_id,
        "source_sheet_id": int(source_sheet_id),
        "destination_spreadsheet_id": destination_spreadsheet_id,
        "new_sheet_id": resp.get("sheetId"),
        "new_title": resp.get("title"),
        "new_index": resp.get("index"),
    }


@mcp.tool()
@handle_drive_errors
async def sheets_freeze(
    spreadsheet_id: str, sheet_id: int, rows: int = 0, cols: int = 0
) -> dict[str, Any]:
    """Freeze the first *rows* rows and *cols* columns of a tab.

    `rows=1` freezes the header row. `rows=0, cols=0` unfreezes everything.
    """
    await _check_safety(spreadsheet_id)
    await asyncio.to_thread(
        api.freeze,
        get_sheets_service(),
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        rows=rows,
        cols=cols,
    )
    return {
        "spreadsheet_id": spreadsheet_id,
        "sheet_id": int(sheet_id),
        "frozen_rows": int(rows),
        "frozen_cols": int(cols),
    }


@mcp.tool()
@handle_drive_errors
async def sheets_merge_cells(
    spreadsheet_id: str,
    sheet_id: int,
    start_row_index: int,
    end_row_index: int,
    start_column_index: int,
    end_column_index: int,
    mode: str = "MERGE_ALL",
) -> dict[str, Any]:
    """Merge or unmerge cells in a GridRange.

    `mode`:
      - ``MERGE_ALL`` (default) — merge into a single cell.
      - ``MERGE_COLUMNS`` — merge each column independently across rows.
      - ``MERGE_ROWS`` — merge each row independently across columns.
      - ``UNMERGE`` — split any merged regions overlapping the range.

    Indices are 0-based; end indices are exclusive.
    """
    await _check_safety(spreadsheet_id)
    sheets_svc = get_sheets_service()
    if mode == "UNMERGE":
        await asyncio.to_thread(
            api.unmerge_cells,
            sheets_svc,
            spreadsheet_id=spreadsheet_id,
            sheet_id=sheet_id,
            start_row_index=start_row_index,
            end_row_index=end_row_index,
            start_column_index=start_column_index,
            end_column_index=end_column_index,
        )
    else:
        if mode not in ("MERGE_ALL", "MERGE_COLUMNS", "MERGE_ROWS"):
            return {
                "error": f"invalid mode {mode!r}; expected one of "
                "MERGE_ALL/MERGE_COLUMNS/MERGE_ROWS/UNMERGE"
            }
        await asyncio.to_thread(
            api.merge_cells,
            sheets_svc,
            spreadsheet_id=spreadsheet_id,
            sheet_id=sheet_id,
            start_row_index=start_row_index,
            end_row_index=end_row_index,
            start_column_index=start_column_index,
            end_column_index=end_column_index,
            merge_type=mode,
        )
    return {
        "spreadsheet_id": spreadsheet_id,
        "sheet_id": int(sheet_id),
        "mode": mode,
    }


@mcp.tool()
@handle_drive_errors
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
