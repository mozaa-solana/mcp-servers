"""Google Docs MCP tools (20).

Positions use **UTF-16 code unit indices** (0-based) as required by the
Docs API. When an ``index`` parameter is omitted, the tool appends to the
end of the document body.

Resolve a ``document_id`` via Drive tools (``drive_search`` /
``drive_list_files``) — it is the same string as the Drive file id.
"""
from __future__ import annotations

import asyncio
from typing import Any

from ..api import docs as api
from ..normalize import extract_text, trim_document, trim_file
from ..safety import assert_in_working_folder
from ._registry import get_config, get_docs_service, get_service, handle_drive_errors, mcp


async def _check_safety(document_id: str) -> None:
    """Apply the working-folder rail using the Drive client (docs writes
    happen *inside* a document, but the document itself is a Drive file).
    """
    cfg = get_config()
    if cfg.working_folder_id:
        await asyncio.to_thread(
            assert_in_working_folder,
            get_service(),
            cfg.working_folder_id,
            document_id,
        )


# --------------------------------------------------------------------------
# Read (2)
# --------------------------------------------------------------------------


@mcp.tool()
@handle_drive_errors
async def docs_get(document_id: str) -> dict[str, Any]:
    """Get full document structure: title, body (paragraphs, tables, lists),
    named ranges, headers/footers, and inline objects.

    Returns a trimmed view suitable for LLM consumption. For plain text
    extraction, use ``docs_get_text`` instead.
    """
    data = await asyncio.to_thread(
        api.get_document, get_docs_service(), document_id=document_id
    )
    return trim_document(data)


@mcp.tool()
@handle_drive_errors
async def docs_get_text(document_id: str) -> dict[str, Any]:
    """Extract plain text from the entire document body.

    Flattens all paragraphs, table cells, and structural elements into a
    single string. Useful for reading a document without structural noise.
    """
    data = await asyncio.to_thread(
        api.get_document, get_docs_service(), document_id=document_id
    )
    text = extract_text(data.get("body"))
    return {
        "document_id": data.get("documentId"),
        "title": data.get("title"),
        "text": text,
        "length": len(text),
    }


# --------------------------------------------------------------------------
# Create (1)
# --------------------------------------------------------------------------


@mcp.tool()
@handle_drive_errors
async def docs_create(title: str, parent_id: str | None = None) -> dict[str, Any]:
    """Create a blank Google Doc, optionally inside a Drive folder.

    On personal Gmail, creation may fail with a quota error (SA has 0 quota).
    Use a Workspace folder / Shared Drive as the parent for reliable creation.
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
                "new document inside the safety boundary"
            )
        }
    data = await asyncio.to_thread(
        api.create_document_via_drive, get_service(), title=title, parent_id=parent_id
    )
    return trim_file(data)


# --------------------------------------------------------------------------
# Write — text editing (3)
# --------------------------------------------------------------------------


@mcp.tool()
@handle_drive_errors
async def docs_insert_text(
    document_id: str, text: str, index: int | None = None
) -> dict[str, Any]:
    """Insert text into a document at the given index (appends to end if omitted).

    Inserting a newline implicitly creates a new paragraph. The index is a
    UTF-16 code unit offset from the start of the document body.
    """
    if not text:
        return {"error": "text must not be empty"}
    await _check_safety(document_id)
    await asyncio.to_thread(
        api.insert_text,
        get_docs_service(),
        document_id=document_id,
        text=text,
        index=index,
    )
    return {"document_id": document_id, "inserted": True}


@mcp.tool()
@handle_drive_errors
async def docs_delete_range(
    document_id: str, start_index: int, end_index: int
) -> dict[str, Any]:
    """Delete content between two indices (UTF-16 code units, 0-based).

    Cannot delete the last newline of the document body. Deleting across
    paragraph boundaries merges the paragraphs.
    """
    if start_index < 0 or end_index <= start_index:
        return {"error": "start_index must be >= 0 and end_index must be > start_index"}
    await _check_safety(document_id)
    await asyncio.to_thread(
        api.delete_range,
        get_docs_service(),
        document_id=document_id,
        start_index=start_index,
        end_index=end_index,
    )
    return {"document_id": document_id, "deleted": True}


@mcp.tool()
@handle_drive_errors
async def docs_replace_text(
    document_id: str,
    find: str,
    replace: str,
    match_case: bool = False,
) -> dict[str, Any]:
    """Replace all instances of text in the document.

    Searches the entire document body. Use ``match_case=True`` for
    case-sensitive matching.
    """
    if not find:
        return {"error": "find must not be empty"}
    await _check_safety(document_id)
    resp = await asyncio.to_thread(
        api.replace_all_text,
        get_docs_service(),
        document_id=document_id,
        find=find,
        replace=replace,
        match_case=match_case,
    )
    occurrences = 0
    for reply in resp.get("replies") or []:
        rat = reply.get("replaceAllText") or {}
        occurrences = rat.get("occurrencesChanged", occurrences)
    return {"document_id": document_id, "occurrences_changed": occurrences}


# --------------------------------------------------------------------------
# Write — styling (2)
# --------------------------------------------------------------------------


@mcp.tool()
@handle_drive_errors
async def docs_update_text_style(
    document_id: str,
    start_index: int,
    end_index: int,
    bold: bool | None = None,
    italic: bool | None = None,
    underline: bool | None = None,
    strikethrough: bool | None = None,
    font_size: float | None = None,
    font_family: str | None = None,
    link_url: str | None = None,
) -> dict[str, Any]:
    """Apply text formatting to a range.

    Only the parameters you pass are changed; omitted parameters are left
    untouched. All indices are UTF-16 code units (0-based).
    """
    ts: dict[str, Any] = {}
    if bold is not None:
        ts["bold"] = bold
    if italic is not None:
        ts["italic"] = italic
    if underline is not None:
        ts["underline"] = underline
    if strikethrough is not None:
        ts["strikethrough"] = strikethrough
    if font_size is not None:
        ts["fontSize"] = {"magnitude": float(font_size), "unit": "PT"}
    if font_family is not None:
        ts["weightedFontFamily"] = {"fontFamily": font_family}
    if link_url is not None:
        ts["link"] = {"url": link_url}
    if not ts:
        return {"error": "at least one style parameter is required"}
    await _check_safety(document_id)
    await asyncio.to_thread(
        api.update_text_style,
        get_docs_service(),
        document_id=document_id,
        start_index=start_index,
        end_index=end_index,
        text_style=ts,
    )
    return {"document_id": document_id, "updated": True}


@mcp.tool()
@handle_drive_errors
async def docs_update_paragraph_style(
    document_id: str,
    start_index: int,
    end_index: int,
    alignment: str | None = None,
    heading: str | None = None,
    indent_start: float | None = None,
    line_spacing: float | None = None,
) -> dict[str, Any]:
    """Set paragraph style: alignment, heading level, indentation, line spacing.

    ``heading`` values: ``TITLE``, ``SUBTITLE``, ``HEADING_1`` through
    ``HEADING_6``, ``NORMAL_TEXT``. ``alignment`` values: ``START``,
    ``CENTER``, ``END``, ``JUSTIFIED``.
    """
    ps: dict[str, Any] = {}
    if alignment is not None:
        ps["alignment"] = alignment
    if heading is not None:
        ps["namedStyleType"] = heading
    if indent_start is not None:
        ps["indentStart"] = {"magnitude": float(indent_start), "unit": "PT"}
    if line_spacing is not None:
        ps["lineSpacing"] = float(line_spacing)
    if not ps:
        return {"error": "at least one style parameter is required"}
    await _check_safety(document_id)
    await asyncio.to_thread(
        api.update_paragraph_style,
        get_docs_service(),
        document_id=document_id,
        start_index=start_index,
        end_index=end_index,
        paragraph_style=ps,
    )
    return {"document_id": document_id, "updated": True}


# --------------------------------------------------------------------------
# Write — lists (2)
# --------------------------------------------------------------------------


@mcp.tool()
@handle_drive_errors
async def docs_create_bullets(
    document_id: str,
    start_index: int,
    end_index: int,
    preset: str = "BULLET_DISC_CIRCLE_SQUARE",
) -> dict[str, Any]:
    """Convert paragraphs in a range to a bullet or numbered list.

    ``preset`` values: ``BULLET_DISC_CIRCLE_SQUARE``, ``BULLET_ARROW_DIAMOND_DISC``,
    ``NUMBERED_DECIMAL_ALPHA_ROMAN``, ``NUMBERED_DECIMAL_NESTED``, and more
    (see Google Docs API ``BulletGlyphPreset``).
    """
    _VALID_PRESETS = {
        "BULLET_DISC_CIRCLE_SQUARE",
        "BULLET_ARROW_DIAMOND_DISC",
        "BULLET_CHECKBOX",
        "BULLET_ALPHA_ALPHA_ALPHA",
        "BULLET_ROMAN_ALPHA_ALPHA",
        "BULLET_DIAMOND_CIRCLE_SQUARE",
        "NUMBERED_DECIMAL_ALPHA_ROMAN",
        "NUMBERED_DECIMAL_NESTED",
        "NUMBERED_UPPER_ALPHA_UPPER_ALPHA",
        "NUMBERED_UPPER_ROMAN_UPPER_ROMAN",
    }
    if preset not in _VALID_PRESETS:
        return {"error": f"invalid preset '{preset}'"}
    await _check_safety(document_id)
    await asyncio.to_thread(
        api.create_bullets,
        get_docs_service(),
        document_id=document_id,
        start_index=start_index,
        end_index=end_index,
        preset=preset,
    )
    return {"document_id": document_id, "created_bullets": True}


@mcp.tool()
@handle_drive_errors
async def docs_delete_bullets(
    document_id: str, start_index: int, end_index: int
) -> dict[str, Any]:
    """Remove bullets / numbering from paragraphs in a range."""
    await _check_safety(document_id)
    await asyncio.to_thread(
        api.delete_bullets,
        get_docs_service(),
        document_id=document_id,
        start_index=start_index,
        end_index=end_index,
    )
    return {"document_id": document_id, "deleted_bullets": True}


# --------------------------------------------------------------------------
# Write — tables (5)
# --------------------------------------------------------------------------


@mcp.tool()
@handle_drive_errors
async def docs_insert_table(
    document_id: str,
    rows: int,
    columns: int,
    index: int | None = None,
) -> dict[str, Any]:
    """Insert a table at the given index (appends to end if omitted).

    A newline is automatically inserted before the table. ``rows`` and
    ``columns`` must be >= 1.
    """
    if rows < 1 or columns < 1:
        return {"error": "rows and columns must be >= 1"}
    await _check_safety(document_id)
    resp = await asyncio.to_thread(
        api.insert_table,
        get_docs_service(),
        document_id=document_id,
        rows=rows,
        columns=columns,
        index=index,
    )
    table = None
    for reply in resp.get("replies") or []:
        ti = reply.get("insertTable") or {}
        if ti:
            table = ti
    return {
        "document_id": document_id,
        "rows": rows,
        "columns": columns,
        "table_start_index": (table or {}).get("tableStartLocation", {}).get("index"),
    }


@mcp.tool()
@handle_drive_errors
async def docs_insert_table_row(
    document_id: str,
    table_start_index: int,
    row_index: int,
    column_index: int = 0,
    insert_below: bool = False,
) -> dict[str, Any]:
    """Insert a row into an existing table.

    ``table_start_index`` is the index of the table's start location in the
    document (find it via ``docs_get``). The new row is inserted above
    (``insert_below=False``) or below (``insert_below=True``) the reference cell.
    """
    await _check_safety(document_id)
    await asyncio.to_thread(
        api.insert_table_row,
        get_docs_service(),
        document_id=document_id,
        table_start_index=table_start_index,
        row_index=row_index,
        column_index=column_index,
        insert_below=insert_below,
    )
    return {"document_id": document_id, "inserted_row": True}


@mcp.tool()
@handle_drive_errors
async def docs_delete_table_row(
    document_id: str,
    table_start_index: int,
    row_index: int,
    column_index: int = 0,
) -> dict[str, Any]:
    """Delete a row from an existing table.

    If the row is the last remaining row, the entire table is deleted.
    """
    await _check_safety(document_id)
    await asyncio.to_thread(
        api.delete_table_row,
        get_docs_service(),
        document_id=document_id,
        table_start_index=table_start_index,
        row_index=row_index,
        column_index=column_index,
    )
    return {"document_id": document_id, "deleted_row": True}


@mcp.tool()
@handle_drive_errors
async def docs_insert_table_column(
    document_id: str,
    table_start_index: int,
    column_index: int,
    row_index: int = 0,
    insert_right: bool = False,
) -> dict[str, Any]:
    """Insert a column into an existing table.

    The new column is inserted to the left (``insert_right=False``) or right
    (``insert_right=True``) of the reference cell.
    """
    await _check_safety(document_id)
    await asyncio.to_thread(
        api.insert_table_column,
        get_docs_service(),
        document_id=document_id,
        table_start_index=table_start_index,
        row_index=row_index,
        column_index=column_index,
        insert_right=insert_right,
    )
    return {"document_id": document_id, "inserted_column": True}


@mcp.tool()
@handle_drive_errors
async def docs_delete_table_column(
    document_id: str,
    table_start_index: int,
    column_index: int,
    row_index: int = 0,
) -> dict[str, Any]:
    """Delete a column from an existing table.

    If the column is the last remaining column, the entire table is deleted.
    """
    await _check_safety(document_id)
    await asyncio.to_thread(
        api.delete_table_column,
        get_docs_service(),
        document_id=document_id,
        table_start_index=table_start_index,
        row_index=row_index,
        column_index=column_index,
    )
    return {"document_id": document_id, "deleted_column": True}


# --------------------------------------------------------------------------
# Write — images (2)
# --------------------------------------------------------------------------


@mcp.tool()
@handle_drive_errors
async def docs_insert_image(
    document_id: str,
    image_uri: str,
    index: int | None = None,
    width_pt: float | None = None,
    height_pt: float | None = None,
) -> dict[str, Any]:
    """Insert an inline image from a URL.

    The image is fetched once at insertion time. Supported formats: PNG, JPEG,
    GIF. Max 50 MB, 25 megapixels. The URI must be publicly accessible.
    Optional ``width_pt`` / ``height_pt`` control the display size in points.
    """
    if not image_uri:
        return {"error": "image_uri must not be empty"}
    await _check_safety(document_id)
    resp = await asyncio.to_thread(
        api.insert_inline_image,
        get_docs_service(),
        document_id=document_id,
        image_uri=image_uri,
        index=index,
        width_pt=width_pt,
        height_pt=height_pt,
    )
    obj_id = None
    for reply in resp.get("replies") or []:
        iii = reply.get("insertInlineImage") or {}
        obj_id = iii.get("objectId")
    return {"document_id": document_id, "inline_object_id": obj_id}


@mcp.tool()
@handle_drive_errors
async def docs_replace_image(
    document_id: str, image_object_id: str, image_uri: str
) -> dict[str, Any]:
    """Replace an existing image in the document with a new image from a URL.

    ``image_object_id`` can be found via ``docs_get`` in the inline_objects
    section. The replacement preserves the original size and position.
    """
    if not image_object_id or not image_uri:
        return {"error": "image_object_id and image_uri must not be empty"}
    await _check_safety(document_id)
    await asyncio.to_thread(
        api.replace_image,
        get_docs_service(),
        document_id=document_id,
        image_object_id=image_object_id,
        image_uri=image_uri,
    )
    return {"document_id": document_id, "image_object_id": image_object_id, "replaced": True}


# --------------------------------------------------------------------------
# Write — headers, footers, footnotes (3)
# --------------------------------------------------------------------------


@mcp.tool()
@handle_drive_errors
async def docs_create_header(document_id: str) -> dict[str, Any]:
    """Create a header in the document.

    Returns the header ID which can be used to insert text into the header
    via ``docs_insert_text`` (using the header's ``segmentId``).
    """
    await _check_safety(document_id)
    resp = await asyncio.to_thread(
        api.create_header, get_docs_service(), document_id=document_id
    )
    header = None
    for reply in resp.get("replies") or []:
        ch = reply.get("createHeader") or {}
        if ch:
            header = ch
    return {
        "document_id": document_id,
        "header_id": (header or {}).get("headerId"),
    }


@mcp.tool()
@handle_drive_errors
async def docs_create_footer(document_id: str) -> dict[str, Any]:
    """Create a footer in the document.

    Returns the footer ID. Insert text into the footer via
    ``docs_insert_text`` (using the footer's ``segmentId``).
    """
    await _check_safety(document_id)
    resp = await asyncio.to_thread(
        api.create_footer, get_docs_service(), document_id=document_id
    )
    footer = None
    for reply in resp.get("replies") or []:
        cf = reply.get("createFooter") or {}
        if cf:
            footer = cf
    return {
        "document_id": document_id,
        "footer_id": (footer or {}).get("footerId"),
    }


@mcp.tool()
@handle_drive_errors
async def docs_create_footnote(
    document_id: str, index: int | None = None
) -> dict[str, Any]:
    """Insert a footnote at the given index (appends to end if omitted).

    Returns the footnote ID. Add content to the footnote via
    ``docs_insert_text`` (using the footnote's ``segmentId``).
    """
    await _check_safety(document_id)
    resp = await asyncio.to_thread(
        api.create_footnote,
        get_docs_service(),
        document_id=document_id,
        index=index,
    )
    footnote = None
    for reply in resp.get("replies") or []:
        cf = reply.get("createFootnote") or {}
        if cf:
            footnote = cf
    return {
        "document_id": document_id,
        "footnote_id": (footnote or {}).get("footnoteId"),
    }
