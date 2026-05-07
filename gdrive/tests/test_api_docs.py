"""Tests for api/docs.py — verify verbs and kwargs sent to googleapiclient."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gdrive_mcp.api import docs as api


def _record(verb_chain) -> dict:
    captured: dict = {}

    def recorder(**kwargs):
        captured.update(kwargs)
        m = MagicMock()
        m.execute.return_value = {}
        return m

    verb_chain().side_effect = recorder
    return captured


@pytest.mark.unit
class TestReadAPI:
    def test_get_document(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.get)
        api.get_document(svc, document_id="DOC1")
        assert captured["documentId"] == "DOC1"
        assert "body" in captured["fields"]

    def test_get_document_custom_fields(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.get)
        api.get_document(svc, document_id="DOC1", fields="documentId,title")
        assert captured["fields"] == "documentId,title"


@pytest.mark.unit
class TestCreateDocument:
    def test_create_document(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.create)
        api.create_document(svc, title="MyDoc")
        assert captured["body"] == {"title": "MyDoc"}


@pytest.mark.unit
class TestCreateDocumentViaDrive:
    def test_create_with_parent(self):
        drive = MagicMock()
        captured = _record(lambda: drive.files.return_value.create)
        api.create_document_via_drive(drive, title="MyDoc", parent_id="P")
        assert captured["body"] == {
            "name": "MyDoc",
            "mimeType": "application/vnd.google-apps.document",
            "parents": ["P"],
        }
        assert captured["fields"] == "id,name,mimeType,parents,webViewLink"
        assert captured["supportsAllDrives"] is True

    def test_create_no_parent(self):
        drive = MagicMock()
        captured = _record(lambda: drive.files.return_value.create)
        api.create_document_via_drive(drive, title="MyDoc")
        assert "parents" not in captured["body"]
        assert captured["body"]["mimeType"] == "application/vnd.google-apps.document"


@pytest.mark.unit
class TestBatchUpdate:
    def test_batch_update(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.batch_update(svc, document_id="DOC1", requests=[{"insertText": {}}])
        assert captured["documentId"] == "DOC1"
        assert captured["body"] == {"requests": [{"insertText": {}}]}


@pytest.mark.unit
class TestInsertText:
    def test_insert_text_with_index(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.insert_text(svc, document_id="DOC1", text="hello", index=5)
        req = captured["body"]["requests"][0]["insertText"]
        assert req["location"] == {"index": 5}
        assert req["text"] == "hello"

    def test_insert_text_end_of_segment(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.insert_text(svc, document_id="DOC1", text="hello")
        req = captured["body"]["requests"][0]["insertText"]
        assert "endOfSegmentLocation" in req
        assert "location" not in req

    def test_insert_text_at_index_zero(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.insert_text(svc, document_id="DOC1", text="start", index=0)
        req = captured["body"]["requests"][0]["insertText"]
        assert req["location"] == {"index": 0}


@pytest.mark.unit
class TestDeleteRange:
    def test_delete_range(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.delete_range(svc, document_id="DOC1", start_index=1, end_index=5)
        req = captured["body"]["requests"][0]["deleteContentRange"]
        assert req["range"] == {"startIndex": 1, "endIndex": 5}


@pytest.mark.unit
class TestReplaceAllText:
    def test_replace_all_text_default(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.replace_all_text(svc, document_id="DOC1", find="foo", replace="bar")
        req = captured["body"]["requests"][0]["replaceAllText"]
        assert req["containsText"]["text"] == "foo"
        assert req["containsText"]["matchCase"] is False
        assert req["replaceText"] == "bar"

    def test_replace_all_text_match_case(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.replace_all_text(
            svc, document_id="DOC1", find="foo", replace="bar", match_case=True
        )
        req = captured["body"]["requests"][0]["replaceAllText"]
        assert req["containsText"]["matchCase"] is True


@pytest.mark.unit
class TestUpdateTextStyle:
    def test_update_text_style(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.update_text_style(
            svc,
            document_id="DOC1",
            start_index=0,
            end_index=5,
            text_style={"bold": True, "fontSize": {"magnitude": 14, "unit": "PT"}},
        )
        req = captured["body"]["requests"][0]["updateTextStyle"]
        assert req["range"] == {"startIndex": 0, "endIndex": 5}
        assert req["textStyle"]["bold"] is True
        assert "bold" in req["fields"]
        assert "fontSize" in req["fields"]


@pytest.mark.unit
class TestUpdateParagraphStyle:
    def test_update_paragraph_style(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.update_paragraph_style(
            svc,
            document_id="DOC1",
            start_index=0,
            end_index=10,
            paragraph_style={"namedStyleType": "HEADING_1"},
        )
        req = captured["body"]["requests"][0]["updateParagraphStyle"]
        assert req["range"] == {"startIndex": 0, "endIndex": 10}
        assert req["paragraphStyle"]["namedStyleType"] == "HEADING_1"
        assert "namedStyleType" in req["fields"]


@pytest.mark.unit
class TestBullets:
    def test_create_bullets(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.create_bullets(svc, document_id="DOC1", start_index=0, end_index=10)
        req = captured["body"]["requests"][0]["createParagraphBullets"]
        assert req["range"] == {"startIndex": 0, "endIndex": 10}
        assert req["bulletPreset"] == "BULLET_DISC_CIRCLE_SQUARE"

    def test_create_bullets_custom_preset(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.create_bullets(
            svc,
            document_id="DOC1",
            start_index=0,
            end_index=5,
            preset="NUMBERED_DECIMAL",
        )
        req = captured["body"]["requests"][0]["createParagraphBullets"]
        assert req["bulletPreset"] == "NUMBERED_DECIMAL"

    def test_delete_bullets(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.delete_bullets(svc, document_id="DOC1", start_index=0, end_index=10)
        req = captured["body"]["requests"][0]["deleteParagraphBullets"]
        assert req["range"] == {"startIndex": 0, "endIndex": 10}


@pytest.mark.unit
class TestTable:
    def test_insert_table_with_index(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.insert_table(svc, document_id="DOC1", rows=3, columns=4, index=10)
        req = captured["body"]["requests"][0]["insertTable"]
        assert req["location"] == {"index": 10}
        assert req["rows"] == 3
        assert req["columns"] == 4

    def test_insert_table_end_of_segment(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.insert_table(svc, document_id="DOC1", rows=2, columns=2)
        req = captured["body"]["requests"][0]["insertTable"]
        assert "endOfSegmentLocation" in req
        assert req["rows"] == 2
        assert req["columns"] == 2


@pytest.mark.unit
class TestTableRow:
    def test_insert_table_row(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.insert_table_row(
            svc,
            document_id="DOC1",
            table_start_index=5,
            row_index=2,
            column_index=1,
            insert_below=True,
        )
        req = captured["body"]["requests"][0]["insertTableRow"]
        assert req["tableCellLocation"]["tableStartLocation"] == {"index": 5}
        assert req["tableCellLocation"]["rowIndex"] == 2
        assert req["tableCellLocation"]["columnIndex"] == 1
        assert req["insertBelow"] is True

    def test_insert_table_row_default_insert_below(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.insert_table_row(
            svc, document_id="DOC1", table_start_index=5, row_index=0
        )
        req = captured["body"]["requests"][0]["insertTableRow"]
        assert req["insertBelow"] is False

    def test_delete_table_row(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.delete_table_row(
            svc, document_id="DOC1", table_start_index=5, row_index=3, column_index=2
        )
        req = captured["body"]["requests"][0]["deleteTableRow"]
        assert req["tableCellLocation"]["tableStartLocation"] == {"index": 5}
        assert req["tableCellLocation"]["rowIndex"] == 3
        assert req["tableCellLocation"]["columnIndex"] == 2


@pytest.mark.unit
class TestTableColumn:
    def test_insert_table_column(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.insert_table_column(
            svc,
            document_id="DOC1",
            table_start_index=5,
            row_index=0,
            column_index=2,
            insert_right=True,
        )
        req = captured["body"]["requests"][0]["insertTableColumn"]
        assert req["tableCellLocation"]["tableStartLocation"] == {"index": 5}
        assert req["tableCellLocation"]["columnIndex"] == 2
        assert req["insertRight"] is True

    def test_insert_table_column_default_insert_right(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.insert_table_column(
            svc, document_id="DOC1", table_start_index=5, column_index=1
        )
        req = captured["body"]["requests"][0]["insertTableColumn"]
        assert req["insertRight"] is False

    def test_delete_table_column(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.delete_table_column(
            svc, document_id="DOC1", table_start_index=5, row_index=0, column_index=1
        )
        req = captured["body"]["requests"][0]["deleteTableColumn"]
        assert req["tableCellLocation"]["tableStartLocation"] == {"index": 5}
        assert req["tableCellLocation"]["columnIndex"] == 1


@pytest.mark.unit
class TestInsertInlineImage:
    def test_insert_image_with_index(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.insert_inline_image(
            svc, document_id="DOC1", image_uri="https://img.png", index=5
        )
        req = captured["body"]["requests"][0]["insertInlineImage"]
        assert req["location"] == {"index": 5}
        assert req["uri"] == "https://img.png"

    def test_insert_image_end_of_segment(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.insert_inline_image(svc, document_id="DOC1", image_uri="https://img.png")
        req = captured["body"]["requests"][0]["insertInlineImage"]
        assert "endOfSegmentLocation" in req
        assert req["uri"] == "https://img.png"

    def test_insert_image_with_size(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.insert_inline_image(
            svc,
            document_id="DOC1",
            image_uri="https://img.png",
            index=5,
            width_pt=100.0,
            height_pt=50.0,
        )
        req = captured["body"]["requests"][0]["insertInlineImage"]
        assert req["objectSize"]["height"] == {"magnitude": 50.0, "unit": "PT"}
        assert req["objectSize"]["width"] == {"magnitude": 100.0, "unit": "PT"}


@pytest.mark.unit
class TestReplaceImage:
    def test_replace_image(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.replace_image(
            svc,
            document_id="DOC1",
            image_object_id="obj1",
            image_uri="https://new.png",
        )
        req = captured["body"]["requests"][0]["replaceImage"]
        assert req["imageObjectId"] == "obj1"
        assert req["uri"] == "https://new.png"
        assert req["imageReplaceMethod"] == "CENTER_CROPPED"


@pytest.mark.unit
class TestHeader:
    def test_create_header_with_section(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.create_header(svc, document_id="DOC1", section_id="SEC1")
        req = captured["body"]["requests"][0]["createHeader"]
        assert req["sectionBreakId"] == "SEC1"

    def test_create_header_no_section(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.create_header(svc, document_id="DOC1")
        req = captured["body"]["requests"][0]["createHeader"]
        assert "sectionBreakId" not in req


@pytest.mark.unit
class TestFooter:
    def test_create_footer_with_section(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.create_footer(svc, document_id="DOC1", section_id="SEC1")
        req = captured["body"]["requests"][0]["createFooter"]
        assert req["sectionBreakId"] == "SEC1"

    def test_create_footer_no_section(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.create_footer(svc, document_id="DOC1")
        req = captured["body"]["requests"][0]["createFooter"]
        assert "sectionBreakId" not in req


@pytest.mark.unit
class TestFootnote:
    def test_create_footnote_with_index(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.create_footnote(svc, document_id="DOC1", index=10)
        req = captured["body"]["requests"][0]["createFootnote"]
        assert req["location"] == {"index": 10}

    def test_create_footnote_end_of_segment(self):
        svc = MagicMock()
        captured = _record(lambda: svc.documents.return_value.batchUpdate)
        api.create_footnote(svc, document_id="DOC1")
        req = captured["body"]["requests"][0]["createFootnote"]
        assert "endOfSegmentLocation" in req
