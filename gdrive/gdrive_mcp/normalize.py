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


def trim_permission(p: dict[str, Any] | None) -> dict[str, Any]:
    p = p or {}
    return {
        "id": p.get("id"),
        "type": p.get("type"),  # user / group / domain / anyone
        "role": p.get("role"),  # owner / organizer / fileOrganizer / writer / commenter / reader
        "email": p.get("emailAddress"),
        "domain": p.get("domain"),
        "name": p.get("displayName"),
        "deleted": p.get("deleted", False),
    }


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
