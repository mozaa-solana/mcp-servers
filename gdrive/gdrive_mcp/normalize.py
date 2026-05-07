"""Pure normalization helpers — drop noisy upstream fields, keep what an LLM needs."""
from __future__ import annotations

from typing import Any, Iterable


# --- MIME helpers ----------------------------------------------------------

GOOGLE_DOC = "application/vnd.google-apps.document"
GOOGLE_SHEET = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDES = "application/vnd.google-apps.presentation"
GOOGLE_DRAWING = "application/vnd.google-apps.drawing"
GOOGLE_FOLDER = "application/vnd.google-apps.folder"

GOOGLE_NATIVE_PREFIX = "application/vnd.google-apps."

# Default export targets when caller doesn't override.
DEFAULT_EXPORT_MIME = {
    GOOGLE_DOC: "text/markdown",
    GOOGLE_SHEET: "text/csv",
    GOOGLE_SLIDES: "text/plain",
    GOOGLE_DRAWING: "image/png",
}

# MIME types we are willing to decode as utf-8 text.
TEXT_MIMES = frozenset(
    {
        "text/plain",
        "text/markdown",
        "text/csv",
        "text/html",
        "text/xml",
        "text/yaml",
        "text/x-yaml",
        "application/json",
        "application/xml",
        "application/yaml",
        "application/javascript",
        "application/x-javascript",
        "application/x-yaml",
        "application/x-sh",
    }
)


def is_google_native(mime: str | None) -> bool:
    return bool(mime) and mime.startswith(GOOGLE_NATIVE_PREFIX) and mime != GOOGLE_FOLDER


def is_folder(mime: str | None) -> bool:
    return mime == GOOGLE_FOLDER


def is_text_like(mime: str | None) -> bool:
    if not mime:
        return False
    if mime in TEXT_MIMES:
        return True
    return mime.startswith("text/")


def default_export_mime(mime: str | None) -> str | None:
    if not mime:
        return None
    return DEFAULT_EXPORT_MIME.get(mime)


# --- Trim helpers ----------------------------------------------------------


def trim_user(u: dict[str, Any] | None) -> dict[str, Any] | None:
    if not u:
        return None
    return {
        "email": u.get("emailAddress"),
        "name": u.get("displayName"),
    }


def trim_file(f: dict[str, Any] | None) -> dict[str, Any]:
    f = f or {}
    return {
        "id": f.get("id"),
        "name": f.get("name"),
        "mimeType": f.get("mimeType"),
        "size": int(f["size"]) if f.get("size") else None,
        "modified": f.get("modifiedTime"),
        "created": f.get("createdTime"),
        "parents": f.get("parents") or [],
        "owners": [trim_user(u) for u in (f.get("owners") or [])],
        "trashed": f.get("trashed", False),
        "url": f.get("webViewLink"),
        "is_folder": is_folder(f.get("mimeType")),
        "is_google_native": is_google_native(f.get("mimeType")),
    }


def trim_revision(r: dict[str, Any] | None) -> dict[str, Any]:
    r = r or {}
    return {
        "id": r.get("id"),
        "modified": r.get("modifiedTime"),
        "size": int(r["size"]) if r.get("size") else None,
        "modified_by": trim_user(r.get("lastModifyingUser")),
        "keep_forever": r.get("keepForever", False),
    }


def trim_spreadsheet(s: dict[str, Any] | None) -> dict[str, Any]:
    """Spreadsheet metadata + flattened tab list."""
    s = s or {}
    props = s.get("properties") or {}
    sheets_out: list[dict[str, Any]] = []
    for sh in s.get("sheets") or []:
        p = sh.get("properties") or {}
        grid = p.get("gridProperties") or {}
        sheets_out.append(
            {
                "sheet_id": p.get("sheetId"),
                "title": p.get("title"),
                "index": p.get("index"),
                "rows": grid.get("rowCount"),
                "cols": grid.get("columnCount"),
                "frozen_rows": grid.get("frozenRowCount"),
                "frozen_cols": grid.get("frozenColumnCount"),
            }
        )
    return {
        "id": s.get("spreadsheetId"),
        "title": props.get("title"),
        "locale": props.get("locale"),
        "time_zone": props.get("timeZone"),
        "url": s.get("spreadsheetUrl"),
        "sheets": sheets_out,
    }


def trim_permission(p: dict[str, Any] | None) -> dict[str, Any]:
    p = p or {}
    return {
        "id": p.get("id"),
        "type": p.get("type"),
        "role": p.get("role"),
        "email": p.get("emailAddress"),
        "domain": p.get("domain"),
        "name": p.get("displayName"),
        "deleted": p.get("deleted", False),
    }


def trim_document(d: dict[str, Any] | None) -> dict[str, Any]:
    d = d or {}
    props = d.get("documentStyle") or {}
    return {
        "id": d.get("documentId"),
        "title": d.get("title"),
        "revision_id": d.get("revisionId"),
        "body": _trim_body(d.get("body")),
        "named_ranges": {
            k: [{"id": nr.get("namedRangeId")}]
            for k, ranges in (d.get("namedRanges") or {}).items()
            for nr in (ranges.get("namedRanges") or [])
        }
        if d.get("namedRanges")
        else {},
        "headers": {
            k: _trim_body(v.get("content"))
            for k, v in (d.get("headers") or {}).items()
        },
        "footers": {
            k: _trim_body(v.get("content"))
            for k, v in (d.get("footers") or {}).items()
        },
        "footnotes": {
            k: _trim_body(v.get("content"))
            for k, v in (d.get("footnotes") or {}).items()
        },
        "inline_objects": {
            k: {
                "object_id": v.get("objectId"),
                "mime_type": (v.get("inlineObjectProperties") or {})
                .get("embeddedObject", {})
                .get("mimeType"),
                "content_uri": (v.get("inlineObjectProperties") or {})
                .get("embeddedObject", {})
                .get("imageProperties", {})
                .get("contentUri"),
            }
            for k, v in (d.get("inlineObjects") or {}).items()
        },
        "document_style": {
            "background_color": (props.get("background") or {}).get("color"),
        },
    }


def _trim_body(body: dict[str, Any] | None) -> dict[str, Any]:
    body = body or {}
    elements = []
    for el in body.get("content") or []:
        out = _trim_structural_element(el)
        if out:
            elements.append(out)
    return {"content": elements}


def _trim_structural_element(el: dict[str, Any]) -> dict[str, Any] | None:
    if "paragraph" in el:
        p = el["paragraph"]
        result: dict[str, Any] = {
            "type": "paragraph",
            "start_index": el.get("startIndex"),
            "end_index": el.get("endIndex"),
        }
        style = p.get("paragraphStyle") or {}
        if style.get("namedStyleType"):
            result["style"] = style["namedStyleType"]
        if style.get("alignment"):
            result["alignment"] = style["alignment"]
        elements_out = []
        for pe in p.get("elements") or []:
            elem_out = _trim_paragraph_element(pe)
            if elem_out:
                elements_out.append(elem_out)
        if elements_out:
            result["elements"] = elements_out
        return result
    if "table" in el:
        t = el["table"]
        rows_out = []
        for row in t.get("tableRows") or []:
            cells_out = []
            for cell in row.get("tableCells") or []:
                cell_elements = []
                for ce in cell.get("content") or []:
                    trimmed = _trim_structural_element(ce)
                    if trimmed:
                        cell_elements.append(trimmed)
                cells_out.append({"content": cell_elements})
            rows_out.append({"cells": cells_out})
        return {
            "type": "table",
            "start_index": el.get("startIndex"),
            "end_index": el.get("endIndex"),
            "rows": len(t.get("tableRows") or []),
            "columns": len(t["tableRows"][0].get("tableCells") or []) if t.get("tableRows") else 0,
            "table_rows": rows_out,
        }
    if "sectionBreak" in el:
        return {
            "type": "section_break",
            "start_index": el.get("startIndex"),
            "end_index": el.get("endIndex"),
        }
    if "tableOfContents" in el:
        return {
            "type": "table_of_contents",
            "start_index": el.get("startIndex"),
            "end_index": el.get("endIndex"),
        }
    return None


def _trim_paragraph_element(pe: dict[str, Any]) -> dict[str, Any] | None:
    tr = pe.get("textRun")
    if tr:
        out: dict[str, Any] = {
            "type": "text",
            "content": tr.get("content", ""),
            "start_index": pe.get("startIndex"),
            "end_index": pe.get("endIndex"),
        }
        ts = tr.get("textStyle") or {}
        if ts.get("bold"):
            out["bold"] = True
        if ts.get("italic"):
            out["italic"] = True
        if ts.get("underline"):
            out["underline"] = True
        if ts.get("strikethrough"):
            out["strikethrough"] = True
        if ts.get("link"):
            url = ts["link"].get("url")
            if url:
                out["link"] = url
        return out
    ir = pe.get("inlineObjectElement")
    if ir:
        return {
            "type": "inline_object",
            "object_id": ir.get("inlineObjectId"),
            "start_index": pe.get("startIndex"),
            "end_index": pe.get("endIndex"),
        }
    if pe.get("pageBreak"):
        return {
            "type": "page_break",
            "start_index": pe.get("startIndex"),
            "end_index": pe.get("endIndex"),
        }
    fn = pe.get("footnoteReference")
    if fn:
        return {
            "type": "footnote_reference",
            "footnote_id": fn.get("footnoteId"),
            "start_index": pe.get("startIndex"),
            "end_index": pe.get("endIndex"),
        }
    if pe.get("horizontalRule"):
        return {
            "type": "horizontal_rule",
            "start_index": pe.get("startIndex"),
            "end_index": pe.get("endIndex"),
        }
    if pe.get("columnBreak"):
        return {
            "type": "column_break",
            "start_index": pe.get("startIndex"),
            "end_index": pe.get("endIndex"),
        }
    if pe.get("equation"):
        return {
            "type": "equation",
            "start_index": pe.get("startIndex"),
            "end_index": pe.get("endIndex"),
        }
    return None


def extract_text(body: dict[str, Any] | None) -> str:
    body = body or {}
    parts: list[str] = []
    for el in body.get("content") or []:
        _collect_text(el, parts)
    return "".join(parts).strip()


def _collect_text(el: dict[str, Any], parts: list[str]) -> None:
    if "paragraph" in el:
        for pe in el["paragraph"].get("elements") or []:
            tr = pe.get("textRun")
            if tr:
                parts.append(tr.get("content", ""))
    elif "table" in el:
        for row in el["table"].get("tableRows") or []:
            for cell in row.get("tableCells") or []:
                for ce in cell.get("content") or []:
                    _collect_text(ce, parts)


# --- Generic helpers -------------------------------------------------------


def clamp(n: Any, lo: int, hi: int) -> int:
    try:
        v = int(n)
    except (TypeError, ValueError):
        v = lo
    return max(lo, min(v, hi))


def paginated(
    data: dict[str, Any],
    items: Iterable[dict[str, Any]],
    *,
    item_key: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    items_list = list(items)
    out: dict[str, Any] = {
        "count": len(items_list),
        item_key: items_list,
        "next_cursor": data.get("nextPageToken"),
    }
    if extra:
        out.update(extra)
    return out
