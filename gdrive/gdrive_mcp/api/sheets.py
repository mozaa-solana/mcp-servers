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
