"""Google Docs v1 REST wrappers.

All functions take a Docs v1 service client (built from the same SA
credentials as the Drive client). Positions use **UTF-16 code unit indices**
(0-based) as required by the Docs API.
"""
from __future__ import annotations

from typing import Any


DOCUMENT_FIELDS = (
    "documentId,title,revisionId,body,"
    "documentStyle(background),"
    "namedRanges,namedStyles,"
    "headers,footers,footnotes,"
    "inlineObjects"
)

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"


# --------------------------------------------------------------------------
# Read
# --------------------------------------------------------------------------


def get_document(
    svc: Any, *, document_id: str, fields: str | None = None
) -> dict[str, Any]:
    """``documents.get`` — full document structure (body, styles, headers, etc.)."""
    return (
        svc.documents()
        .get(documentId=document_id, fields=fields or DOCUMENT_FIELDS)
        .execute()
    )


# --------------------------------------------------------------------------
# Create — uses Drive API so we can specify a parent folder
# --------------------------------------------------------------------------


def create_document(
    svc: Any, *, title: str
) -> dict[str, Any]:
    """``documents.create`` — bare Docs endpoint (cannot set parent folder)."""
    return (
        svc.documents()
        .create(body={"title": title})
        .execute()
    )


def create_document_via_drive(
    drive_svc: Any, *, title: str, parent_id: str | None = None
) -> dict[str, Any]:
    """Create an empty Google Doc via Drive API so we can place it in *parent_id*.

    The bare ``documents.create`` Docs endpoint cannot specify a parent;
    going through Drive lets us create-and-place atomically. Returns the Drive
    file metadata (``id`` is the document id).
    """
    body: dict[str, Any] = {"name": title, "mimeType": GOOGLE_DOC_MIME}
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


# --------------------------------------------------------------------------
# Write — generic batchUpdate
# --------------------------------------------------------------------------


def batch_update(
    svc: Any, *, document_id: str, requests: list[dict[str, Any]]
) -> dict[str, Any]:
    """``documents.batchUpdate`` — generic mutation endpoint."""
    return (
        svc.documents()
        .batchUpdate(documentId=document_id, body={"requests": requests})
        .execute()
    )


# --------------------------------------------------------------------------
# Write — text editing
# --------------------------------------------------------------------------


def insert_text(
    svc: Any,
    *,
    document_id: str,
    text: str,
    index: int | None = None,
) -> dict[str, Any]:
    """insertText — insert text at *index* or append to end of body."""
    location: dict[str, Any]
    if index is not None:
        location = {"index": int(index)}
        req: dict[str, Any] = {"insertText": {"location": location, "text": text}}
    else:
        location = {}
        req = {"insertText": {"endOfSegmentLocation": location, "text": text}}
    return batch_update(svc, document_id=document_id, requests=[req])


def delete_range(
    svc: Any,
    *,
    document_id: str,
    start_index: int,
    end_index: int,
) -> dict[str, Any]:
    """deleteContentRange — remove content between two UTF-16 indices."""
    req = {
        "deleteContentRange": {
            "range": {"startIndex": int(start_index), "endIndex": int(end_index)}
        }
    }
    return batch_update(svc, document_id=document_id, requests=[req])


def replace_all_text(
    svc: Any,
    *,
    document_id: str,
    find: str,
    replace: str,
    match_case: bool = False,
) -> dict[str, Any]:
    """replaceAllText — replace every occurrence of *find* with *replace*."""
    req = {
        "replaceAllText": {
            "containsText": {"text": find, "matchCase": match_case},
            "replaceText": replace,
        }
    }
    return batch_update(svc, document_id=document_id, requests=[req])


# --------------------------------------------------------------------------
# Write — styling
# --------------------------------------------------------------------------


def update_text_style(
    svc: Any,
    *,
    document_id: str,
    start_index: int,
    end_index: int,
    text_style: dict[str, Any],
) -> dict[str, Any]:
    """updateTextStyle — apply text formatting (bold, italic, font, etc.) to a range."""
    req = {
        "updateTextStyle": {
            "range": {"startIndex": int(start_index), "endIndex": int(end_index)},
            "textStyle": text_style,
            "fields": ",".join(text_style.keys()),
        }
    }
    return batch_update(svc, document_id=document_id, requests=[req])


def update_paragraph_style(
    svc: Any,
    *,
    document_id: str,
    start_index: int,
    end_index: int,
    paragraph_style: dict[str, Any],
) -> dict[str, Any]:
    """updateParagraphStyle — set alignment, heading level, indentation, etc."""
    req = {
        "updateParagraphStyle": {
            "range": {"startIndex": int(start_index), "endIndex": int(end_index)},
            "paragraphStyle": paragraph_style,
            "fields": ",".join(paragraph_style.keys()),
        }
    }
    return batch_update(svc, document_id=document_id, requests=[req])


# --------------------------------------------------------------------------
# Write — lists
# --------------------------------------------------------------------------


def create_bullets(
    svc: Any,
    *,
    document_id: str,
    start_index: int,
    end_index: int,
    preset: str = "BULLET_DISC_CIRCLE_SQUARE",
) -> dict[str, Any]:
    """createParagraphBullets — convert paragraphs to a bullet/numbered list."""
    req = {
        "createParagraphBullets": {
            "range": {"startIndex": int(start_index), "endIndex": int(end_index)},
            "bulletPreset": preset,
        }
    }
    return batch_update(svc, document_id=document_id, requests=[req])


def delete_bullets(
    svc: Any,
    *,
    document_id: str,
    start_index: int,
    end_index: int,
) -> dict[str, Any]:
    """deleteParagraphBullets — remove bullets/numbering from a range."""
    req = {
        "deleteParagraphBullets": {
            "range": {"startIndex": int(start_index), "endIndex": int(end_index)}
        }
    }
    return batch_update(svc, document_id=document_id, requests=[req])


# --------------------------------------------------------------------------
# Write — tables
# --------------------------------------------------------------------------


def insert_table(
    svc: Any,
    *,
    document_id: str,
    rows: int,
    columns: int,
    index: int | None = None,
) -> dict[str, Any]:
    """insertTable — create a new table at *index* or end of body."""
    location: dict[str, Any]
    if index is not None:
        location = {"index": int(index)}
        req: dict[str, Any] = {
            "insertTable": {"location": location, "rows": int(rows), "columns": int(columns)}
        }
    else:
        location = {}
        req = {
            "insertTable": {
                "endOfSegmentLocation": location,
                "rows": int(rows),
                "columns": int(columns),
            }
        }
    return batch_update(svc, document_id=document_id, requests=[req])


def insert_table_row(
    svc: Any,
    *,
    document_id: str,
    table_start_index: int,
    row_index: int,
    column_index: int = 0,
    insert_below: bool = False,
) -> dict[str, Any]:
    """insertTableRow — add a row above or below the reference cell."""
    req = {
        "insertTableRow": {
            "tableCellLocation": {
                "tableStartLocation": {"index": int(table_start_index)},
                "rowIndex": int(row_index),
                "columnIndex": int(column_index),
            },
            "insertBelow": insert_below,
        }
    }
    return batch_update(svc, document_id=document_id, requests=[req])


def delete_table_row(
    svc: Any,
    *,
    document_id: str,
    table_start_index: int,
    row_index: int,
    column_index: int = 0,
) -> dict[str, Any]:
    """deleteTableRow — remove a row from a table."""
    req = {
        "deleteTableRow": {
            "tableCellLocation": {
                "tableStartLocation": {"index": int(table_start_index)},
                "rowIndex": int(row_index),
                "columnIndex": int(column_index),
            }
        }
    }
    return batch_update(svc, document_id=document_id, requests=[req])


def insert_table_column(
    svc: Any,
    *,
    document_id: str,
    table_start_index: int,
    row_index: int = 0,
    column_index: int,
    insert_right: bool = False,
) -> dict[str, Any]:
    """insertTableColumn — add a column to the left or right of the reference cell."""
    req = {
        "insertTableColumn": {
            "tableCellLocation": {
                "tableStartLocation": {"index": int(table_start_index)},
                "rowIndex": int(row_index),
                "columnIndex": int(column_index),
            },
            "insertRight": insert_right,
        }
    }
    return batch_update(svc, document_id=document_id, requests=[req])


def delete_table_column(
    svc: Any,
    *,
    document_id: str,
    table_start_index: int,
    row_index: int = 0,
    column_index: int,
) -> dict[str, Any]:
    """deleteTableColumn — remove a column from a table."""
    req = {
        "deleteTableColumn": {
            "tableCellLocation": {
                "tableStartLocation": {"index": int(table_start_index)},
                "rowIndex": int(row_index),
                "columnIndex": int(column_index),
            }
        }
    }
    return batch_update(svc, document_id=document_id, requests=[req])


# --------------------------------------------------------------------------
# Write — images
# --------------------------------------------------------------------------


def insert_inline_image(
    svc: Any,
    *,
    document_id: str,
    image_uri: str,
    index: int | None = None,
    width_pt: float | None = None,
    height_pt: float | None = None,
) -> dict[str, Any]:
    """insertInlineImage — insert an image from a URL at *index* or end of body."""
    location: dict[str, Any]
    if index is not None:
        location = {"index": int(index)}
    else:
        location = {}
    image_req: dict[str, Any] = {"uri": image_uri}
    if width_pt is not None or height_pt is not None:
        size: dict[str, Any] = {}
        if height_pt is not None:
            size["height"] = {"magnitude": float(height_pt), "unit": "PT"}
        if width_pt is not None:
            size["width"] = {"magnitude": float(width_pt), "unit": "PT"}
        image_req["objectSize"] = size
    if index is not None:
        req: dict[str, Any] = {"insertInlineImage": {"location": location, **image_req}}
    else:
        req = {"insertInlineImage": {"endOfSegmentLocation": location, **image_req}}
    return batch_update(svc, document_id=document_id, requests=[req])


def replace_image(
    svc: Any,
    *,
    document_id: str,
    image_object_id: str,
    image_uri: str,
) -> dict[str, Any]:
    """replaceImage — swap an existing inline image for a new one from a URL."""
    req = {
        "replaceImage": {
            "imageObjectId": image_object_id,
            "uri": image_uri,
            "imageReplaceMethod": "CENTER_CROPPED",
        }
    }
    return batch_update(svc, document_id=document_id, requests=[req])


# --------------------------------------------------------------------------
# Write — headers, footers, footnotes
# --------------------------------------------------------------------------


def create_header(
    svc: Any, *, document_id: str, section_id: str | None = None
) -> dict[str, Any]:
    """createHeader — add a header to the document (optionally scoped to a section)."""
    body: dict[str, Any] = {}
    if section_id is not None:
        body["sectionBreakId"] = section_id
    req = {"createHeader": body}
    return batch_update(svc, document_id=document_id, requests=[req])


def create_footer(
    svc: Any, *, document_id: str, section_id: str | None = None
) -> dict[str, Any]:
    """createFooter — add a footer to the document (optionally scoped to a section)."""
    body: dict[str, Any] = {}
    if section_id is not None:
        body["sectionBreakId"] = section_id
    req = {"createFooter": body}
    return batch_update(svc, document_id=document_id, requests=[req])


def create_footnote(
    svc: Any, *, document_id: str, index: int | None = None
) -> dict[str, Any]:
    """createFootnote — insert a footnote at *index* or end of body."""
    if index is not None:
        req: dict[str, Any] = {
            "createFootnote": {"location": {"index": int(index)}}
        }
    else:
        req = {"createFootnote": {"endOfSegmentLocation": {}}}
    return batch_update(svc, document_id=document_id, requests=[req])
