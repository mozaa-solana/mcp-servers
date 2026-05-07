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
    extract_text,
    is_folder,
    is_google_native,
    is_text_like,
    paginated,
    trim_document,
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


@pytest.mark.unit
class TestTrimDocument:
    def test_basic_paragraph(self):
        doc = {
            "documentId": "D1",
            "title": "Test",
            "revisionId": "R1",
            "body": {
                "content": [
                    {
                        "startIndex": 1,
                        "endIndex": 6,
                        "paragraph": {
                            "elements": [
                                {
                                    "startIndex": 1,
                                    "endIndex": 6,
                                    "textRun": {"content": "Hello"},
                                }
                            ]
                        },
                    }
                ]
            },
        }
        out = trim_document(doc)
        assert out["id"] == "D1"
        assert out["title"] == "Test"
        assert len(out["body"]["content"]) == 1
        assert out["body"]["content"][0]["type"] == "paragraph"

    def test_table_of_contents(self):
        doc = {
            "documentId": "D1",
            "title": "T",
            "body": {
                "content": [
                    {
                        "startIndex": 1,
                        "endIndex": 10,
                        "tableOfContents": {},
                    }
                ]
            },
        }
        out = trim_document(doc)
        assert out["body"]["content"][0]["type"] == "table_of_contents"

    def test_section_break(self):
        doc = {
            "documentId": "D1",
            "title": "T",
            "body": {
                "content": [
                    {
                        "startIndex": 1,
                        "endIndex": 2,
                        "sectionBreak": {},
                    }
                ]
            },
        }
        out = trim_document(doc)
        assert out["body"]["content"][0]["type"] == "section_break"

    def test_table_with_rows_and_columns(self):
        doc = {
            "documentId": "D1",
            "title": "T",
            "body": {
                "content": [
                    {
                        "startIndex": 1,
                        "endIndex": 20,
                        "table": {
                            "tableRows": [
                                {
                                    "tableCells": [
                                        {
                                            "content": [
                                                {
                                                    "paragraph": {
                                                        "elements": [
                                                            {"textRun": {"content": "A1"}}
                                                        ]
                                                    }
                                                }
                                            ]
                                        },
                                        {
                                            "content": [
                                                {
                                                    "paragraph": {
                                                        "elements": [
                                                            {"textRun": {"content": "B1"}}
                                                        ]
                                                    }
                                                }
                                            ]
                                        },
                                    ]
                                }
                            ]
                        },
                    }
                ]
            },
        }
        out = trim_document(doc)
        table = out["body"]["content"][0]
        assert table["type"] == "table"
        assert table["rows"] == 1
        assert table["columns"] == 2

    def test_headers_with_content(self):
        doc = {
            "documentId": "D1",
            "title": "T",
            "body": {"content": []},
            "headers": {
                "h_1": {
                    "headerId": "h_1",
                    "content": {
                        "content": [
                            {
                                "paragraph": {
                                    "elements": [{"textRun": {"content": "Header text"}}]
                                }
                            }
                        ]
                    },
                }
            },
        }
        out = trim_document(doc)
        assert "h_1" in out["headers"]
        assert out["headers"]["h_1"]["content"][0]["type"] == "paragraph"

    def test_footers_with_content(self):
        doc = {
            "documentId": "D1",
            "title": "T",
            "body": {"content": []},
            "footers": {
                "f_1": {
                    "footerId": "f_1",
                    "content": {
                        "content": [
                            {
                                "paragraph": {
                                    "elements": [{"textRun": {"content": "Footer text"}}]
                                }
                            }
                        ]
                    },
                }
            },
        }
        out = trim_document(doc)
        assert "f_1" in out["footers"]
        assert out["footers"]["f_1"]["content"][0]["type"] == "paragraph"

    def test_footnotes_with_content(self):
        doc = {
            "documentId": "D1",
            "title": "T",
            "body": {"content": []},
            "footnotes": {
                "fn_1": {
                    "footnoteId": "fn_1",
                    "content": {
                        "content": [
                            {
                                "paragraph": {
                                    "elements": [{"textRun": {"content": "Footnote text"}}]
                                }
                            }
                        ]
                    },
                }
            },
        }
        out = trim_document(doc)
        assert "fn_1" in out["footnotes"]
        assert out["footnotes"]["fn_1"]["content"][0]["type"] == "paragraph"

    def test_named_ranges_no_redundant_name(self):
        doc = {
            "documentId": "D1",
            "title": "T",
            "body": {"content": []},
            "namedRanges": {
                "myRange": {
                    "namedRanges": [
                        {"namedRangeId": "nr_1", "name": "myRange"}
                    ]
                }
            },
        }
        out = trim_document(doc)
        assert out["named_ranges"]["myRange"] == [{"id": "nr_1"}]

    def test_inline_objects_separates_mime_and_uri(self):
        doc = {
            "documentId": "D1",
            "title": "T",
            "body": {"content": []},
            "inlineObjects": {
                "obj_1": {
                    "objectId": "obj_1",
                    "inlineObjectProperties": {
                        "embeddedObject": {
                            "mimeType": "image/png",
                            "imageProperties": {
                                "contentUri": "https://example.com/img.png"
                            },
                        }
                    },
                }
            },
        }
        out = trim_document(doc)
        obj = out["inline_objects"]["obj_1"]
        assert obj["object_id"] == "obj_1"
        assert obj["mime_type"] == "image/png"
        assert obj["content_uri"] == "https://example.com/img.png"

    def test_handles_none(self):
        out = trim_document(None)
        assert out["id"] is None
        assert out["body"] == {"content": []}

    def test_empty_body(self):
        out = trim_document({"documentId": "D1", "body": {"content": []}})
        assert out["body"]["content"] == []

    def test_document_style(self):
        doc = {
            "documentId": "D1",
            "title": "T",
            "body": {"content": []},
            "documentStyle": {
                "background": {"color": {"rgbColor": {"red": 1, "green": 1, "blue": 1}}}
            },
        }
        out = trim_document(doc)
        assert out["document_style"]["background_color"] is not None


@pytest.mark.unit
class TestExtractText:
    def test_single_paragraph(self):
        body = {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "Hello "}},
                            {"textRun": {"content": "World"}},
                        ]
                    }
                }
            ]
        }
        assert extract_text(body) == "Hello World"

    def test_multiple_paragraphs(self):
        body = {
            "content": [
                {"paragraph": {"elements": [{"textRun": {"content": "Line 1"}}]}},
                {"paragraph": {"elements": [{"textRun": {"content": "\n"}}]}},
                {"paragraph": {"elements": [{"textRun": {"content": "Line 2"}}]}},
            ]
        }
        assert "Line 1" in extract_text(body)
        assert "Line 2" in extract_text(body)

    def test_table_cells(self):
        body = {
            "content": [
                {
                    "table": {
                        "tableRows": [
                            {
                                "tableCells": [
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {"textRun": {"content": "A1"}}
                                                    ]
                                                }
                                            }
                                        ]
                                    },
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {"textRun": {"content": "B1"}}
                                                    ]
                                                }
                                            }
                                        ]
                                    },
                                ]
                            }
                        ]
                    }
                }
            ]
        }
        text = extract_text(body)
        assert "A1" in text
        assert "B1" in text

    def test_empty_body(self):
        assert extract_text({"content": []}) == ""

    def test_none_body(self):
        assert extract_text(None) == ""

    def test_mixed_paragraph_and_table(self):
        body = {
            "content": [
                {"paragraph": {"elements": [{"textRun": {"content": "Intro "}}]}},
                {
                    "table": {
                        "tableRows": [
                            {
                                "tableCells": [
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {"textRun": {"content": "cell"}}
                                                    ]
                                                }
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                },
                {"paragraph": {"elements": [{"textRun": {"content": "outro"}}]}},
            ]
        }
        text = extract_text(body)
        assert "Intro" in text
        assert "cell" in text
        assert "outro" in text
