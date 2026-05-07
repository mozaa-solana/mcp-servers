"""Google Sheets v4 REST wrappers.

All functions take a Sheets v4 service client (built from the same SA
credentials as the Drive client). Range strings use **A1 notation** —
e.g. ``Sheet1!A1:B10``, ``'My Sheet'!A:B``, ``Sheet1!A:A``.
"""
from __future__ import annotations

from typing import Any


SPREADSHEET_FIELDS = (
    "spreadsheetId,spreadsheetUrl,"
    "properties(title,locale,timeZone),"
    "sheets(properties(sheetId,title,index,gridProperties))"
)


# --------------------------------------------------------------------------
# Read
# --------------------------------------------------------------------------


def get_spreadsheet(
    svc: Any, *, spreadsheet_id: str, fields: str | None = None
) -> dict[str, Any]:
    """``spreadsheets.get`` — metadata + list of sheets/tabs."""
    return (
        svc.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields=fields or SPREADSHEET_FIELDS)
        .execute()
    )


def get_values(
    svc: Any,
    *,
    spreadsheet_id: str,
    range_: str,
    value_render: str = "FORMATTED_VALUE",
    major_dim: str = "ROWS",
) -> dict[str, Any]:
    """``spreadsheets.values.get`` — read a single range."""
    return (
        svc.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=range_,
            valueRenderOption=value_render,
            majorDimension=major_dim,
        )
        .execute()
    )


def batch_get_values(
    svc: Any,
    *,
    spreadsheet_id: str,
    ranges: list[str],
    value_render: str = "FORMATTED_VALUE",
    major_dim: str = "ROWS",
) -> dict[str, Any]:
    """``spreadsheets.values.batchGet`` — read multiple ranges in one call."""
    return (
        svc.spreadsheets()
        .values()
        .batchGet(
            spreadsheetId=spreadsheet_id,
            ranges=ranges,
            valueRenderOption=value_render,
            majorDimension=major_dim,
        )
        .execute()
    )


# --------------------------------------------------------------------------
# Write — values
# --------------------------------------------------------------------------


def update_values(
    svc: Any,
    *,
    spreadsheet_id: str,
    range_: str,
    values: list[list[Any]],
    value_input: str = "USER_ENTERED",
) -> dict[str, Any]:
    """``spreadsheets.values.update`` — overwrite cells in a range."""
    return (
        svc.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=range_,
            valueInputOption=value_input,
            body={"values": values},
        )
        .execute()
    )


def append_values(
    svc: Any,
    *,
    spreadsheet_id: str,
    range_: str,
    values: list[list[Any]],
    value_input: str = "USER_ENTERED",
    insert_data_option: str = "INSERT_ROWS",
) -> dict[str, Any]:
    """``spreadsheets.values.append`` — append rows after the last row of data."""
    return (
        svc.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=range_,
            valueInputOption=value_input,
            insertDataOption=insert_data_option,
            body={"values": values},
        )
        .execute()
    )


def clear_values(
    svc: Any, *, spreadsheet_id: str, range_: str
) -> dict[str, Any]:
    """``spreadsheets.values.clear`` — empty the cells in a range."""
    return (
        svc.spreadsheets()
        .values()
        .clear(spreadsheetId=spreadsheet_id, range=range_, body={})
        .execute()
    )


def batch_update_values(
    svc: Any,
    *,
    spreadsheet_id: str,
    data: list[dict[str, Any]],
    value_input: str = "USER_ENTERED",
) -> dict[str, Any]:
    """``spreadsheets.values.batchUpdate`` — multi-range overwrite.

    *data* is a list of ``{"range": "Sheet1!A1:B2", "values": [[...]]}``.
    """
    body = {"valueInputOption": value_input, "data": data}
    return (
        svc.spreadsheets()
        .values()
        .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
        .execute()
    )


# --------------------------------------------------------------------------
# Write — structure (tab CRUD via spreadsheets.batchUpdate)
# --------------------------------------------------------------------------


def batch_update_structure(
    svc: Any, *, spreadsheet_id: str, requests: list[dict[str, Any]]
) -> dict[str, Any]:
    """``spreadsheets.batchUpdate`` — generic structural mutation.

    *requests* is a list of typed mutation objects: ``addSheet``,
    ``deleteSheet``, ``updateSheetProperties``, ``duplicateSheet``, etc.
    """
    return (
        svc.spreadsheets()
        .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
        .execute()
    )


# --------------------------------------------------------------------------
# Create — uses Drive API so we can specify a parent folder
# --------------------------------------------------------------------------


SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"


def copy_sheet_to(
    svc: Any,
    *,
    source_spreadsheet_id: str,
    source_sheet_id: int,
    destination_spreadsheet_id: str,
) -> dict[str, Any]:
    """``spreadsheets.sheets.copyTo`` — copy a tab into a *different* spreadsheet.

    Returns the new sheet's properties (sheetId, title, index) inside the
    destination spreadsheet. The source remains unchanged.
    """
    return (
        svc.spreadsheets()
        .sheets()
        .copyTo(
            spreadsheetId=source_spreadsheet_id,
            sheetId=int(source_sheet_id),
            body={"destinationSpreadsheetId": destination_spreadsheet_id},
        )
        .execute()
    )


# --- Convenience wrappers around batch_update_structure ---

def find_replace(
    svc: Any,
    *,
    spreadsheet_id: str,
    find: str,
    replace: str,
    sheet_id: int | None = None,
    match_case: bool = False,
    match_entire_cell: bool = False,
) -> dict[str, Any]:
    """findReplace request. Scope: a single sheet (``sheet_id``) or all sheets."""
    req: dict[str, Any] = {
        "findReplace": {
            "find": find,
            "replacement": replace,
            "matchCase": match_case,
            "matchEntireCell": match_entire_cell,
        }
    }
    if sheet_id is not None:
        req["findReplace"]["sheetId"] = int(sheet_id)
    else:
        req["findReplace"]["allSheets"] = True
    return batch_update_structure(svc, spreadsheet_id=spreadsheet_id, requests=[req])


def insert_dimension(
    svc: Any,
    *,
    spreadsheet_id: str,
    sheet_id: int,
    dimension: str,  # "ROWS" | "COLUMNS"
    start_index: int,
    count: int,
) -> dict[str, Any]:
    """insertDimension — insert *count* blank rows/cols starting at *start_index* (0-based)."""
    req = {
        "insertDimension": {
            "range": {
                "sheetId": int(sheet_id),
                "dimension": dimension,
                "startIndex": int(start_index),
                "endIndex": int(start_index) + int(count),
            },
            "inheritFromBefore": False,
        }
    }
    return batch_update_structure(svc, spreadsheet_id=spreadsheet_id, requests=[req])


def delete_dimension(
    svc: Any,
    *,
    spreadsheet_id: str,
    sheet_id: int,
    dimension: str,
    start_index: int,
    count: int,
) -> dict[str, Any]:
    """deleteDimension — remove *count* rows/cols starting at *start_index* (0-based)."""
    req = {
        "deleteDimension": {
            "range": {
                "sheetId": int(sheet_id),
                "dimension": dimension,
                "startIndex": int(start_index),
                "endIndex": int(start_index) + int(count),
            }
        }
    }
    return batch_update_structure(svc, spreadsheet_id=spreadsheet_id, requests=[req])


def sort_range(
    svc: Any,
    *,
    spreadsheet_id: str,
    sheet_id: int,
    start_row_index: int,
    end_row_index: int,
    start_column_index: int,
    end_column_index: int,
    sort_column_index: int,
    descending: bool = False,
) -> dict[str, Any]:
    """sortRange — sort cells within a GridRange by one column."""
    req = {
        "sortRange": {
            "range": {
                "sheetId": int(sheet_id),
                "startRowIndex": int(start_row_index),
                "endRowIndex": int(end_row_index),
                "startColumnIndex": int(start_column_index),
                "endColumnIndex": int(end_column_index),
            },
            "sortSpecs": [
                {
                    "dimensionIndex": int(sort_column_index),
                    "sortOrder": "DESCENDING" if descending else "ASCENDING",
                }
            ],
        }
    }
    return batch_update_structure(svc, spreadsheet_id=spreadsheet_id, requests=[req])


def freeze(
    svc: Any,
    *,
    spreadsheet_id: str,
    sheet_id: int,
    rows: int = 0,
    cols: int = 0,
) -> dict[str, Any]:
    """updateSheetProperties — freeze the first *rows* rows and *cols* columns."""
    req = {
        "updateSheetProperties": {
            "properties": {
                "sheetId": int(sheet_id),
                "gridProperties": {
                    "frozenRowCount": int(rows),
                    "frozenColumnCount": int(cols),
                },
            },
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
        }
    }
    return batch_update_structure(svc, spreadsheet_id=spreadsheet_id, requests=[req])


def merge_cells(
    svc: Any,
    *,
    spreadsheet_id: str,
    sheet_id: int,
    start_row_index: int,
    end_row_index: int,
    start_column_index: int,
    end_column_index: int,
    merge_type: str = "MERGE_ALL",  # MERGE_ALL | MERGE_COLUMNS | MERGE_ROWS
) -> dict[str, Any]:
    """mergeCells — merge a GridRange according to *merge_type*."""
    req = {
        "mergeCells": {
            "range": {
                "sheetId": int(sheet_id),
                "startRowIndex": int(start_row_index),
                "endRowIndex": int(end_row_index),
                "startColumnIndex": int(start_column_index),
                "endColumnIndex": int(end_column_index),
            },
            "mergeType": merge_type,
        }
    }
    return batch_update_structure(svc, spreadsheet_id=spreadsheet_id, requests=[req])


def unmerge_cells(
    svc: Any,
    *,
    spreadsheet_id: str,
    sheet_id: int,
    start_row_index: int,
    end_row_index: int,
    start_column_index: int,
    end_column_index: int,
) -> dict[str, Any]:
    """unmergeCells — split any merged regions overlapping the GridRange."""
    req = {
        "unmergeCells": {
            "range": {
                "sheetId": int(sheet_id),
                "startRowIndex": int(start_row_index),
                "endRowIndex": int(end_row_index),
                "startColumnIndex": int(start_column_index),
                "endColumnIndex": int(end_column_index),
            }
        }
    }
    return batch_update_structure(svc, spreadsheet_id=spreadsheet_id, requests=[req])


def create_via_drive(
    drive_svc: Any, *, title: str, parent_id: str | None = None
) -> dict[str, Any]:
    """Create an empty spreadsheet via Drive API so we can place it in *parent_id*.

    The bare ``spreadsheets.create`` Sheets endpoint cannot specify a parent;
    going through Drive lets us create-and-place atomically. Returns the Drive
    file metadata (``id`` is the spreadsheet id).
    """
    body: dict[str, Any] = {"name": title, "mimeType": SPREADSHEET_MIME}
    if parent_id:
        body["parents"] = [parent_id]
    return (
        drive_svc.files()
        .create(
            body=body,
            fields="id,name,mimeType,parents,webViewLink",
            supportsAllDrives=True,
        )
        .execute()
    )
