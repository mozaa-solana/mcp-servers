"""Tests for tools/sheets.py — read, write values, structure, safety rail."""
from __future__ import annotations

import pytest

from gdrive_mcp.safety import SafetyViolation
from gdrive_mcp.tools import sheets as tools
from tests.conftest import (
    program_files_create,
    program_files_get,
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
