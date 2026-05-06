"""Tests for pure normalization helpers."""
from __future__ import annotations

import pytest

from gdrive_mcp.normalize import (
    DEFAULT_EXPORT_MIME,
    GOOGLE_DOC,
    GOOGLE_FOLDER,
    GOOGLE_SHEET,
    GOOGLE_SLIDES,
    clamp,
    default_export_mime,
    is_folder,
    is_google_native,
    is_text_like,
    paginated,
    trim_file,
    trim_permission,
    trim_revision,
    trim_user,
)


@pytest.mark.unit
class TestMimeHelpers:
    @pytest.mark.parametrize(
        "mime,expected",
        [
            (GOOGLE_DOC, True),
            (GOOGLE_SHEET, True),
            (GOOGLE_SLIDES, True),
            (GOOGLE_FOLDER, False),  # folder is not "native content"
            ("application/pdf", False),
            ("text/plain", False),
            (None, False),
        ],
    )
    def test_is_google_native(self, mime, expected):
        assert is_google_native(mime) is expected

    def test_is_folder(self):
        assert is_folder(GOOGLE_FOLDER) is True
        assert is_folder("text/plain") is False

    @pytest.mark.parametrize(
        "mime,expected",
        [
            ("text/plain", True),
            ("text/markdown", True),
            ("application/json", True),
            ("application/pdf", False),
            ("image/png", False),
            (None, False),
        ],
    )
    def test_is_text_like(self, mime, expected):
        assert is_text_like(mime) is expected

    def test_default_export_mime_for_doc(self):
        assert default_export_mime(GOOGLE_DOC) == DEFAULT_EXPORT_MIME[GOOGLE_DOC]
        assert default_export_mime(GOOGLE_SHEET) == "text/csv"

    def test_default_export_mime_unknown(self):
        assert default_export_mime("text/plain") is None
        assert default_export_mime(None) is None


@pytest.mark.unit
class TestTrimFile:
    def test_extracts_canonical_fields(self):
        out = trim_file(
            {
                "id": "abc",
                "name": "doc.md",
                "mimeType": "text/markdown",
                "size": "1024",
                "modifiedTime": "2026-05-01T00:00:00Z",
                "createdTime": "2026-04-01T00:00:00Z",
                "parents": ["P1"],
                "owners": [{"emailAddress": "u@x.com", "displayName": "U"}],
                "trashed": False,
                "webViewLink": "https://drive.google.com/...",
            }
        )
        assert out["id"] == "abc"
        assert out["size"] == 1024
        assert out["owners"] == [{"email": "u@x.com", "name": "U"}]
        assert out["is_folder"] is False
        assert out["is_google_native"] is False

    def test_size_none_when_missing(self):
        assert trim_file({"id": "1"})["size"] is None

    def test_folder_flag_set(self):
        out = trim_file({"id": "f", "mimeType": GOOGLE_FOLDER})
        assert out["is_folder"] is True
        assert out["is_google_native"] is False

    def test_native_flag_set(self):
        out = trim_file({"id": "d", "mimeType": GOOGLE_DOC})
        assert out["is_google_native"] is True

    def test_handles_none(self):
        out = trim_file(None)
        assert out["id"] is None
        assert out["owners"] == []


@pytest.mark.unit
class TestTrimUserRevisionPermission:
    def test_trim_user_none(self):
        assert trim_user(None) is None

    def test_trim_user(self):
        assert trim_user({"emailAddress": "a@b", "displayName": "A"}) == {
            "email": "a@b",
            "name": "A",
        }

    def test_trim_revision(self):
        out = trim_revision(
            {
                "id": "r1",
                "modifiedTime": "2026-05-01T00:00:00Z",
                "size": "42",
                "lastModifyingUser": {"emailAddress": "u@x", "displayName": "U"},
                "keepForever": True,
            }
        )
        assert out == {
            "id": "r1",
            "modified": "2026-05-01T00:00:00Z",
            "size": 42,
            "modified_by": {"email": "u@x", "name": "U"},
            "keep_forever": True,
        }

    def test_trim_permission(self):
        out = trim_permission(
            {
                "id": "p1",
                "type": "user",
                "role": "writer",
                "emailAddress": "u@x",
                "displayName": "U",
            }
        )
        assert out["role"] == "writer"
        assert out["email"] == "u@x"
        assert out["deleted"] is False


@pytest.mark.unit
class TestHelpers:
    @pytest.mark.parametrize(
        "raw,lo,hi,expected",
        [(5, 1, 10, 5), (-3, 1, 10, 1), (999, 1, 50, 50), ("abc", 1, 5, 1), (None, 0, 10, 0)],
    )
    def test_clamp(self, raw, lo, hi, expected):
        assert clamp(raw, lo, hi) == expected

    def test_paginated_envelope(self):
        out = paginated(
            {"nextPageToken": "abc"},
            [{"x": 1}, {"x": 2}],
            item_key="files",
            extra={"query": "q"},
        )
        assert out == {
            "count": 2,
            "files": [{"x": 1}, {"x": 2}],
            "next_cursor": "abc",
            "query": "q",
        }
