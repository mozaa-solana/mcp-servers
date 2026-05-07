"""Tests for tools/docs.py — 20 Google Docs MCP tools."""
from __future__ import annotations

import pytest

from gdrive_mcp.tools import docs as tools
from tests.conftest import (
    program_documents_batch_update,
    program_documents_create,
    program_documents_get,
    program_files_create,
    program_files_get,
    program_files_get_per_id,
)


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsGet:
    async def test_returns_trimmed(self, docs_svc):
        program_documents_get(
            docs_svc,
            {
                "documentId": "D1",
                "title": "My Doc",
                "body": {
                    "content": [
                        {
                            "startIndex": 1,
                            "endIndex": 10,
                            "paragraph": {
                                "elements": [
                                    {
                                        "startIndex": 1,
                                        "endIndex": 10,
                                        "textRun": {"content": "Hello"},
                                    }
                                ]
                            },
                        }
                    ]
                },
            },
        )
        out = await tools.docs_get("D1")
        assert out["id"] == "D1"
        assert out["title"] == "My Doc"


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsGetText:
    async def test_extracts_text(self, docs_svc):
        program_documents_get(
            docs_svc,
            {
                "documentId": "D1",
                "title": "My Doc",
                "body": {
                    "content": [
                        {
                            "paragraph": {
                                "elements": [
                                    {"textRun": {"content": "Hello "}},
                                    {"textRun": {"content": "World"}},
                                ]
                            }
                        },
                        {
                            "paragraph": {
                                "elements": [{"textRun": {"content": "\n"}}]
                            }
                        },
                    ]
                },
            },
        )
        out = await tools.docs_get_text("D1")
        assert out["document_id"] == "D1"
        assert out["title"] == "My Doc"
        assert "Hello" in out["text"]
        assert out["length"] == len(out["text"])


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsCreate:
    async def test_creates_via_drive(self, svc):
        program_files_create(
            svc,
            {
                "id": "NEW_DOC",
                "name": "Test Doc",
                "mimeType": "application/vnd.google-apps.document",
            },
        )
        out = await tools.docs_create("Test Doc")
        assert out["id"] == "NEW_DOC"

    async def test_with_parent_id(self, svc):
        program_files_create(
            svc,
            {
                "id": "NEW_DOC",
                "name": "Test Doc",
                "mimeType": "application/vnd.google-apps.document",
            },
        )
        out = await tools.docs_create("Test Doc", parent_id="FOLDER1")
        assert out["id"] == "NEW_DOC"

    async def test_safety_rail_requires_parent(self, svc_with_safety):
        drive_stub, _root = svc_with_safety
        out = await tools.docs_create("Test Doc")
        assert "GDRIVE_WORKING_FOLDER_ID" in out["error"]

    async def test_safety_rail_blocks_outside_parent(self, svc_with_safety):
        drive_stub, _root = svc_with_safety
        program_files_get(drive_stub, {"parents": []})
        out = await tools.docs_create("Test Doc", parent_id="OUTSIDE")
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_safety_rail_allows_inside_parent(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get(drive_stub, {"parents": [root]})
        program_files_create(
            drive_stub,
            {
                "id": "NEW_DOC",
                "name": "Test Doc",
                "mimeType": "application/vnd.google-apps.document",
            },
        )
        out = await tools.docs_create("Test Doc", parent_id="INSIDE")
        assert out["id"] == "NEW_DOC"


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsInsertText:
    async def test_success(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        out = await tools.docs_insert_text("D1", "Hello")
        assert out["document_id"] == "D1"
        assert out["inserted"] is True

    async def test_with_index(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        out = await tools.docs_insert_text("D1", "Hi", index=5)
        assert out["inserted"] is True

    async def test_empty_text_validation(self, docs_svc):
        out = await tools.docs_insert_text("D1", "")
        assert "empty" in out["error"]

    async def test_insert_at_index_zero(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        out = await tools.docs_insert_text("D1", "Hi", index=0)
        assert out["inserted"] is True


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsDeleteRange:
    async def test_success(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        out = await tools.docs_delete_range("D1", 1, 5)
        assert out["document_id"] == "D1"
        assert out["deleted"] is True

    async def test_invalid_range_start_ge_end(self, docs_svc):
        out = await tools.docs_delete_range("D1", 5, 5)
        assert "end_index must be > start_index" in out["error"]

    async def test_invalid_range_negative_start(self, docs_svc):
        out = await tools.docs_delete_range("D1", -1, 5)
        assert "start_index must be >= 0" in out["error"]


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsReplaceText:
    async def test_success(self, docs_svc):
        program_documents_batch_update(
            docs_svc,
            {"replies": [{"replaceAllText": {"occurrencesChanged": 3}}]},
        )
        out = await tools.docs_replace_text("D1", "old", "new")
        assert out["document_id"] == "D1"
        assert out["occurrences_changed"] == 3

    async def test_empty_find_validation(self, docs_svc):
        out = await tools.docs_replace_text("D1", "", "new")
        assert "empty" in out["error"]


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsUpdateTextStyle:
    async def test_bold_italic(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        out = await tools.docs_update_text_style("D1", 1, 5, bold=True, italic=True)
        assert out["document_id"] == "D1"
        assert out["updated"] is True

    async def test_sends_correct_style_fields(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        await tools.docs_update_text_style(
            "D1", 1, 5, bold=True, font_size=14, font_family="Arial"
        )
        body = docs_svc.documents.return_value.batchUpdate.call_args.kwargs["body"]
        ts = body["requests"][0]["updateTextStyle"]["textStyle"]
        assert ts["bold"] is True
        assert ts["fontSize"] == {"magnitude": 14, "unit": "PT"}
        assert ts["weightedFontFamily"]["fontFamily"] == "Arial"

    async def test_no_style_param_validation(self, docs_svc):
        out = await tools.docs_update_text_style("D1", 1, 5)
        assert "at least one style parameter" in out["error"]

    async def test_sends_link_url(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        await tools.docs_update_text_style("D1", 1, 5, link_url="https://example.com")
        body = docs_svc.documents.return_value.batchUpdate.call_args.kwargs["body"]
        ts = body["requests"][0]["updateTextStyle"]["textStyle"]
        assert ts["link"] == {"url": "https://example.com"}

    async def test_font_size_as_float(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        await tools.docs_update_text_style("D1", 1, 5, font_size=10.5)
        body = docs_svc.documents.return_value.batchUpdate.call_args.kwargs["body"]
        ts = body["requests"][0]["updateTextStyle"]["textStyle"]
        assert ts["fontSize"] == {"magnitude": 10.5, "unit": "PT"}


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsUpdateParagraphStyle:
    async def test_with_heading(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        out = await tools.docs_update_paragraph_style("D1", 1, 5, heading="HEADING_1")
        assert out["document_id"] == "D1"
        assert out["updated"] is True

    async def test_sends_correct_paragraph_fields(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        await tools.docs_update_paragraph_style(
            "D1", 1, 5, alignment="CENTER", indent_start=36.0
        )
        body = docs_svc.documents.return_value.batchUpdate.call_args.kwargs["body"]
        ps = body["requests"][0]["updateParagraphStyle"]["paragraphStyle"]
        assert ps["alignment"] == "CENTER"
        assert ps["indentStart"] == {"magnitude": 36.0, "unit": "PT"}

    async def test_no_style_param_validation(self, docs_svc):
        out = await tools.docs_update_paragraph_style("D1", 1, 5)
        assert "at least one style parameter" in out["error"]

    async def test_sends_line_spacing(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        await tools.docs_update_paragraph_style("D1", 1, 5, line_spacing=1.5)
        body = docs_svc.documents.return_value.batchUpdate.call_args.kwargs["body"]
        ps = body["requests"][0]["updateParagraphStyle"]["paragraphStyle"]
        assert ps["lineSpacing"] == 1.5


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsCreateBullets:
    async def test_success(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        out = await tools.docs_create_bullets("D1", 1, 10)
        assert out["document_id"] == "D1"
        assert out["created_bullets"] is True

    async def test_custom_preset(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        out = await tools.docs_create_bullets("D1", 1, 10, preset="NUMBERED_DECIMAL_ALPHA_ROMAN")
        assert out["created_bullets"] is True

    async def test_invalid_preset(self, docs_svc):
        out = await tools.docs_create_bullets("D1", 1, 10, preset="INVALID_PRESET")
        assert "invalid preset" in out["error"]


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsDeleteBullets:
    async def test_success(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        out = await tools.docs_delete_bullets("D1", 1, 10)
        assert out["document_id"] == "D1"
        assert out["deleted_bullets"] is True


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsInsertTable:
    async def test_success(self, docs_svc):
        program_documents_batch_update(
            docs_svc,
            {"replies": [{"insertTable": {"tableStartLocation": {"index": 10}}}]},
        )
        out = await tools.docs_insert_table("D1", 3, 4)
        assert out["document_id"] == "D1"
        assert out["rows"] == 3
        assert out["columns"] == 4
        assert out["table_start_index"] == 10

    async def test_rows_less_than_one(self, docs_svc):
        out = await tools.docs_insert_table("D1", 0, 3)
        assert "must be >= 1" in out["error"]

    async def test_cols_less_than_one(self, docs_svc):
        out = await tools.docs_insert_table("D1", 3, 0)
        assert "must be >= 1" in out["error"]


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsInsertTableRow:
    async def test_success(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        out = await tools.docs_insert_table_row("D1", 10, 1, column_index=0)
        assert out["document_id"] == "D1"
        assert out["inserted_row"] is True


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsDeleteTableRow:
    async def test_success(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        out = await tools.docs_delete_table_row("D1", 10, 1)
        assert out["document_id"] == "D1"
        assert out["deleted_row"] is True


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsInsertTableColumn:
    async def test_success(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        out = await tools.docs_insert_table_column("D1", 10, 1)
        assert out["document_id"] == "D1"
        assert out["inserted_column"] is True


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsDeleteTableColumn:
    async def test_success(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        out = await tools.docs_delete_table_column("D1", 10, 1)
        assert out["document_id"] == "D1"
        assert out["deleted_column"] is True


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsInsertImage:
    async def test_success(self, docs_svc):
        program_documents_batch_update(
            docs_svc,
            {"replies": [{"insertInlineImage": {"objectId": "IMG1"}}]},
        )
        out = await tools.docs_insert_image("D1", "https://example.com/img.png")
        assert out["document_id"] == "D1"
        assert out["inline_object_id"] == "IMG1"

    async def test_empty_uri_validation(self, docs_svc):
        out = await tools.docs_insert_image("D1", "")
        assert "empty" in out["error"]


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsReplaceImage:
    async def test_success(self, docs_svc):
        program_documents_batch_update(docs_svc, {"replies": []})
        out = await tools.docs_replace_image("D1", "IMG1", "https://example.com/new.png")
        assert out["document_id"] == "D1"
        assert out["image_object_id"] == "IMG1"
        assert out["replaced"] is True

    async def test_empty_object_id_validation(self, docs_svc):
        out = await tools.docs_replace_image("D1", "", "https://example.com/new.png")
        assert "must not be empty" in out["error"]

    async def test_empty_uri_validation(self, docs_svc):
        out = await tools.docs_replace_image("D1", "IMG1", "")
        assert "must not be empty" in out["error"]


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsCreateHeader:
    async def test_success(self, docs_svc):
        program_documents_batch_update(
            docs_svc,
            {"replies": [{"createHeader": {"headerId": "H1"}}]},
        )
        out = await tools.docs_create_header("D1")
        assert out["document_id"] == "D1"
        assert out["header_id"] == "H1"


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsCreateFooter:
    async def test_success(self, docs_svc):
        program_documents_batch_update(
            docs_svc,
            {"replies": [{"createFooter": {"footerId": "F1"}}]},
        )
        out = await tools.docs_create_footer("D1")
        assert out["document_id"] == "D1"
        assert out["footer_id"] == "F1"


@pytest.mark.asyncio
@pytest.mark.unit
class TestDocsCreateFootnote:
    async def test_with_index(self, docs_svc):
        program_documents_batch_update(
            docs_svc,
            {"replies": [{"createFootnote": {"footnoteId": "FN1"}}]},
        )
        out = await tools.docs_create_footnote("D1", index=5)
        assert out["document_id"] == "D1"
        assert out["footnote_id"] == "FN1"

    async def test_without_index(self, docs_svc):
        program_documents_batch_update(
            docs_svc,
            {"replies": [{"createFootnote": {"footnoteId": "FN2"}}]},
        )
        out = await tools.docs_create_footnote("D1")
        assert out["document_id"] == "D1"
        assert out["footnote_id"] == "FN2"


@pytest.mark.asyncio
@pytest.mark.unit
class TestSafetyRail:
    async def test_insert_text_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}, "D_INSIDE": {"parents": [root]}})
        out = await tools.docs_insert_text("D_OUTSIDE", "text")
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_insert_text_allows_inside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        docs_stub = drive_stub._docs_stub
        program_files_get_per_id(drive_stub, {"D_INSIDE": {"parents": [root]}})
        program_documents_batch_update(docs_stub, {"replies": []})
        out = await tools.docs_insert_text("D_INSIDE", "text")
        assert out["inserted"] is True

    async def test_delete_range_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_delete_range("D_OUTSIDE", 1, 5)
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_replace_text_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_replace_text("D_OUTSIDE", "x", "y")
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_create_bullets_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_create_bullets("D_OUTSIDE", 1, 10)
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_insert_table_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_insert_table("D_OUTSIDE", 2, 2)
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_insert_image_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_insert_image("D_OUTSIDE", "https://example.com/img.png")
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_create_header_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_create_header("D_OUTSIDE")
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_update_text_style_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_update_text_style("D_OUTSIDE", 1, 5, bold=True)
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_update_paragraph_style_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_update_paragraph_style("D_OUTSIDE", 1, 5, heading="HEADING_1")
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_delete_bullets_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_delete_bullets("D_OUTSIDE", 1, 10)
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_insert_table_row_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_insert_table_row("D_OUTSIDE", 10, 1)
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_delete_table_row_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_delete_table_row("D_OUTSIDE", 10, 1)
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_insert_table_column_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_insert_table_column("D_OUTSIDE", 10, 1)
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_delete_table_column_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_delete_table_column("D_OUTSIDE", 10, 1)
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_replace_image_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_replace_image("D_OUTSIDE", "IMG1", "https://example.com/new.png")
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_create_footer_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_create_footer("D_OUTSIDE")
        assert out.get("violation") == "working_folder", f"unexpected: {out}"

    async def test_create_footnote_blocks_outside(self, svc_with_safety):
        drive_stub, root = svc_with_safety
        program_files_get_per_id(drive_stub, {"D_OUTSIDE": {"parents": []}})
        out = await tools.docs_create_footnote("D_OUTSIDE")
        assert out.get("violation") == "working_folder", f"unexpected: {out}"
