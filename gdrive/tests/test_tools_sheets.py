"""Tests for tools/sheets.py — read, write values, structure, safety rail."""
from __future__ import annotations

import pytest

from gdrive_mcp.safety import SafetyViolation
from gdrive_mcp.tools import sheets as tools
from tests.conftest import (
    program_files_create,
    program_files_get,
    program_sheets_copy_to,
    program_spreadsheet_get,
    program_structure_batch_update,
    program_values_append,
    program_values_batch_get,
    program_values_batch_update,
    program_values_clear,
    program_values_get,
    program_values_update,
)


# --------------------------------------------------------------------------
# Read
# --------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetMetadata:
    async def test_returns_trimmed(self, sheets_svc):
        program_spreadsheet_get(
            sheets_svc,
            {
                "spreadsheetId": "SS",
                "spreadsheetUrl": "https://docs.google.com/...",
                "properties": {"title": "Q4", "locale": "en_US", "timeZone": "UTC"},
                "sheets": [
                    {
                        "properties": {
                            "sheetId": 0,
                            "title": "Sheet1",
                            "index": 0,
                            "gridProperties": {"rowCount": 100, "columnCount": 26},
                        }
                    },
                    {
                        "properties": {
                            "sheetId": 1234567890,
                            "title": "Data",
                            "index": 1,
                            "gridProperties": {"rowCount": 1000, "columnCount": 10},
                        }
                    },
                ],
            },
        )

        out = await tools.sheets_get_metadata("SS")

        assert out["title"] == "Q4"
        assert out["locale"] == "en_US"
        assert len(out["sheets"]) == 2
        assert out["sheets"][1]["sheet_id"] == 1234567890
        assert out["sheets"][1]["rows"] == 1000


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetValues:
    async def test_returns_values(self, sheets_svc):
        program_values_get(
            sheets_svc,
            {
                "range": "Sheet1!A1:B2",
                "majorDimension": "ROWS",
                "values": [["a", "b"], [1, 2]],
            },
        )

        out = await tools.sheets_get_values("SS", "Sheet1!A1:B2")

        assert out["values"] == [["a", "b"], [1, 2]]
        assert out["range"] == "Sheet1!A1:B2"
        assert out["spreadsheet_id"] == "SS"

    async def test_passes_value_render_through(self, sheets_svc):
        program_values_get(sheets_svc, {"values": []})
        await tools.sheets_get_values("SS", "A1", value_render="FORMULA")
        kwargs = sheets_svc.spreadsheets.return_value.values.return_value.get.call_args.kwargs
        assert kwargs["valueRenderOption"] == "FORMULA"

    async def test_empty_values_default_to_list(self, sheets_svc):
        program_values_get(sheets_svc, {"range": "A1"})
        out = await tools.sheets_get_values("SS", "A1")
        assert out["values"] == []


@pytest.mark.asyncio
@pytest.mark.unit
class TestBatchGet:
    async def test_rejects_empty_ranges(self, sheets_svc):
        out = await tools.sheets_batch_get_values("SS", [])
        assert "non-empty" in out["error"]

    async def test_returns_each_range(self, sheets_svc):
        program_values_batch_get(
            sheets_svc,
            {
                "valueRanges": [
                    {"range": "A1:B1", "majorDimension": "ROWS", "values": [["x", "y"]]},
                    {"range": "C1:C2", "majorDimension": "ROWS", "values": [["a"], ["b"]]},
                ]
            },
        )
        out = await tools.sheets_batch_get_values("SS", ["A1:B1", "C1:C2"])
        assert len(out["ranges"]) == 2
        assert out["ranges"][0]["values"] == [["x", "y"]]


# --------------------------------------------------------------------------
# Write — values
# --------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
class TestUpdateValues:
    async def test_returns_summary(self, sheets_svc):
        program_values_update(
            sheets_svc,
            {
                "updatedRange": "Sheet1!A1:B2",
                "updatedRows": 2,
                "updatedColumns": 2,
                "updatedCells": 4,
            },
        )
        out = await tools.sheets_update_values("SS", "Sheet1!A1", [[1, 2], [3, 4]])
        assert out["updated_cells"] == 4

    async def test_rejects_non_list_values(self, sheets_svc):
        out = await tools.sheets_update_values("SS", "A1", "not-a-list")
        assert "2-D list" in out["error"]

    async def test_safety_rail_blocks(self, sheets_svc_with_safety):
        drive_stub, sheets_stub, _root = sheets_svc_with_safety
        program_files_get(drive_stub, {"parents": []})  # outside rail
        with pytest.raises(SafetyViolation):
            await tools.sheets_update_values("SS_OUTSIDE", "A1", [[1]])

    async def test_safety_rail_allows_inside(self, sheets_svc_with_safety):
        drive_stub, sheets_stub, root = sheets_svc_with_safety
        program_files_get(drive_stub, {"parents": [root]})
        program_values_update(sheets_stub, {"updatedCells": 1})
        out = await tools.sheets_update_values("SS_INSIDE", "A1", [[1]])
        assert out["updated_cells"] == 1


@pytest.mark.asyncio
@pytest.mark.unit
class TestAppendValues:
    async def test_returns_updated_range_from_updates_block(self, sheets_svc):
        program_values_append(
            sheets_svc,
            {"updates": {"updatedRange": "Sheet1!A5:B5", "updatedRows": 1, "updatedCells": 2}},
        )
        out = await tools.sheets_append_values("SS", "Sheet1!A:B", [["x", "y"]])
        assert out["updated_range"] == "Sheet1!A5:B5"
        assert out["updated_rows"] == 1


@pytest.mark.asyncio
@pytest.mark.unit
class TestClearAndBatch:
    async def test_clear(self, sheets_svc):
        program_values_clear(sheets_svc, {"clearedRange": "Sheet1!A1:B2"})
        out = await tools.sheets_clear_values("SS", "Sheet1!A1:B2")
        assert out["cleared_range"] == "Sheet1!A1:B2"

    async def test_batch_update_rejects_empty(self, sheets_svc):
        out = await tools.sheets_batch_update_values("SS", [])
        assert "non-empty" in out["error"]

    async def test_batch_update_summary(self, sheets_svc):
        program_values_batch_update(
            sheets_svc,
            {
                "totalUpdatedRows": 3,
                "totalUpdatedCells": 6,
                "responses": [
                    {"updatedRange": "A1:B1", "updatedCells": 2},
                    {"updatedRange": "C1:D1", "updatedCells": 4},
                ],
            },
        )
        out = await tools.sheets_batch_update_values(
            "SS",
            [
                {"range": "A1:B1", "values": [[1, 2]]},
                {"range": "C1:D1", "values": [[3, 4]]},
            ],
        )
        assert out["total_updated_cells"] == 6
        assert len(out["responses"]) == 2


# --------------------------------------------------------------------------
# Write — structure
# --------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
class TestCreateSpreadsheet:
    async def test_creates_via_drive(self, svc):
        program_files_create(
            svc,
            {
                "id": "NEW",
                "name": "X",
                "mimeType": "application/vnd.google-apps.spreadsheet",
            },
        )
        out = await tools.sheets_create_spreadsheet("X")
        assert out["id"] == "NEW"

    async def test_safety_rail_requires_parent(self, svc_with_safety):
        out = await tools.sheets_create_spreadsheet("X")
        assert "GDRIVE_WORKING_FOLDER_ID" in out["error"]


@pytest.mark.asyncio
@pytest.mark.unit
class TestStructureMutations:
    async def test_add_sheet_returns_new_props(self, sheets_svc):
        program_structure_batch_update(
            sheets_svc,
            {
                "replies": [
                    {
                        "addSheet": {
                            "properties": {"sheetId": 99, "title": "New", "index": 1}
                        }
                    }
                ]
            },
        )
        out = await tools.sheets_add_sheet("SS", "New")
        assert out["sheet_id"] == 99
        assert out["title"] == "New"

    async def test_delete_sheet_records_id(self, sheets_svc):
        program_structure_batch_update(sheets_svc, {"replies": [{"deleteSheet": {}}]})
        out = await tools.sheets_delete_sheet("SS", 99)
        assert out["deleted_sheet_id"] == 99

    async def test_rename_sends_correct_request(self, sheets_svc):
        program_structure_batch_update(sheets_svc, {"replies": [{"updateSheetProperties": {}}]})
        await tools.sheets_rename_sheet("SS", 0, "Renamed")
        body = sheets_svc.spreadsheets.return_value.batchUpdate.call_args.kwargs["body"]
        assert body["requests"][0]["updateSheetProperties"]["properties"]["title"] == "Renamed"
        assert body["requests"][0]["updateSheetProperties"]["fields"] == "title"

    async def test_find_replace_returns_summary(self, sheets_svc):
        program_structure_batch_update(
            sheets_svc,
            {
                "replies": [
                    {
                        "findReplace": {
                            "occurrencesChanged": 7,
                            "valuesChanged": 5,
                            "rowsChanged": 3,
                            "sheetsChanged": 1,
                        }
                    }
                ]
            },
        )
        out = await tools.sheets_find_replace("SS", find="x", replace="y", sheet_id=0)
        assert out["occurrences_changed"] == 7
        body = sheets_svc.spreadsheets.return_value.batchUpdate.call_args.kwargs["body"]
        fr = body["requests"][0]["findReplace"]
        assert fr["sheetId"] == 0
        assert "allSheets" not in fr

    async def test_find_replace_all_sheets_when_sheet_id_none(self, sheets_svc):
        program_structure_batch_update(sheets_svc, {"replies": [{"findReplace": {}}]})
        await tools.sheets_find_replace("SS", "x", "y")
        body = sheets_svc.spreadsheets.return_value.batchUpdate.call_args.kwargs["body"]
        assert body["requests"][0]["findReplace"]["allSheets"] is True

    @pytest.mark.parametrize("count,err", [(0, "count must be"), (-1, "count must be")])
    async def test_insert_rows_rejects_invalid_count(self, sheets_svc, count, err):
        out = await tools.sheets_insert_rows("SS", 0, 1, count)
        assert err in out["error"]

    async def test_insert_rows_sends_correct_request(self, sheets_svc):
        program_structure_batch_update(sheets_svc, {"replies": [{"insertDimension": {}}]})
        await tools.sheets_insert_rows("SS", sheet_id=0, start_index=2, count=3)
        body = sheets_svc.spreadsheets.return_value.batchUpdate.call_args.kwargs["body"]
        rng = body["requests"][0]["insertDimension"]["range"]
        assert rng["dimension"] == "ROWS"
        assert (rng["startIndex"], rng["endIndex"]) == (2, 5)

    async def test_delete_rows_sends_correct_request(self, sheets_svc):
        program_structure_batch_update(sheets_svc, {"replies": [{"deleteDimension": {}}]})
        await tools.sheets_delete_rows("SS", sheet_id=0, start_index=1, count=2)
        body = sheets_svc.spreadsheets.return_value.batchUpdate.call_args.kwargs["body"]
        rng = body["requests"][0]["deleteDimension"]["range"]
        assert rng["dimension"] == "ROWS"
        assert (rng["startIndex"], rng["endIndex"]) == (1, 3)

    async def test_insert_cols(self, sheets_svc):
        program_structure_batch_update(sheets_svc, {"replies": [{"insertDimension": {}}]})
        await tools.sheets_insert_cols("SS", sheet_id=0, start_index=4, count=1)
        body = sheets_svc.spreadsheets.return_value.batchUpdate.call_args.kwargs["body"]
        assert body["requests"][0]["insertDimension"]["range"]["dimension"] == "COLUMNS"

    async def test_delete_cols(self, sheets_svc):
        program_structure_batch_update(sheets_svc, {"replies": [{"deleteDimension": {}}]})
        await tools.sheets_delete_cols("SS", sheet_id=0, start_index=0, count=2)
        body = sheets_svc.spreadsheets.return_value.batchUpdate.call_args.kwargs["body"]
        assert body["requests"][0]["deleteDimension"]["range"]["dimension"] == "COLUMNS"

    async def test_sort_range_descending(self, sheets_svc):
        program_structure_batch_update(sheets_svc, {"replies": [{"sortRange": {}}]})
        out = await tools.sheets_sort_range(
            "SS", sheet_id=0,
            start_row_index=0, end_row_index=10,
            start_column_index=0, end_column_index=3,
            sort_column_index=1, descending=True,
        )
        assert out["order"] == "DESCENDING"
        body = sheets_svc.spreadsheets.return_value.batchUpdate.call_args.kwargs["body"]
        spec = body["requests"][0]["sortRange"]["sortSpecs"][0]
        assert spec == {"dimensionIndex": 1, "sortOrder": "DESCENDING"}


@pytest.mark.asyncio
@pytest.mark.unit
class TestCopySheetTo:
    async def test_returns_new_props(self, sheets_svc):
        program_sheets_copy_to(
            sheets_svc, {"sheetId": 99, "title": "Copy of X", "index": 1}
        )
        out = await tools.sheets_copy_sheet_to_spreadsheet("SS1", 0, "SS2")
        assert out["new_sheet_id"] == 99
        assert out["destination_spreadsheet_id"] == "SS2"

    async def test_safety_rail_on_destination(self, sheets_svc_with_safety):
        drive_stub, sheets_stub, _ = sheets_svc_with_safety
        program_files_get(drive_stub, {"parents": []})  # dest outside rail
        with pytest.raises(SafetyViolation):
            await tools.sheets_copy_sheet_to_spreadsheet("SS1", 0, "SS2_OUTSIDE")


@pytest.mark.asyncio
@pytest.mark.unit
class TestFreezeAndMerge:
    async def test_freeze_sets_grid_props(self, sheets_svc):
        program_structure_batch_update(
            sheets_svc, {"replies": [{"updateSheetProperties": {}}]}
        )
        out = await tools.sheets_freeze("SS", sheet_id=0, rows=1, cols=2)
        assert out["frozen_rows"] == 1
        assert out["frozen_cols"] == 2

    async def test_merge_default_mode(self, sheets_svc):
        program_structure_batch_update(sheets_svc, {"replies": [{"mergeCells": {}}]})
        out = await tools.sheets_merge_cells("SS", 0, 0, 2, 0, 3)
        assert out["mode"] == "MERGE_ALL"
        body = sheets_svc.spreadsheets.return_value.batchUpdate.call_args.kwargs["body"]
        assert body["requests"][0]["mergeCells"]["mergeType"] == "MERGE_ALL"

    async def test_merge_unmerge_mode_uses_unmerge_request(self, sheets_svc):
        program_structure_batch_update(sheets_svc, {"replies": [{"unmergeCells": {}}]})
        await tools.sheets_merge_cells("SS", 0, 0, 2, 0, 3, mode="UNMERGE")
        body = sheets_svc.spreadsheets.return_value.batchUpdate.call_args.kwargs["body"]
        assert "unmergeCells" in body["requests"][0]
        assert "mergeCells" not in body["requests"][0]

    async def test_merge_invalid_mode(self, sheets_svc):
        out = await tools.sheets_merge_cells("SS", 0, 0, 2, 0, 3, mode="MERGE_FOO")
        assert "invalid mode" in out["error"]


@pytest.mark.asyncio
@pytest.mark.unit
class TestStructureMutations2:
    async def test_duplicate_sheet(self, sheets_svc):
        program_structure_batch_update(
            sheets_svc,
            {
                "replies": [
                    {
                        "duplicateSheet": {
                            "properties": {"sheetId": 200, "title": "Copy", "index": 2}
                        }
                    }
                ]
            },
        )
        out = await tools.sheets_duplicate_sheet("SS", 0, "Copy")
        assert out["sheet_id"] == 200
        assert out["source_sheet_id"] == 0
