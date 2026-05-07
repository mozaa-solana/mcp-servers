"""Tests for api/sheets.py — verify verbs and kwargs sent to googleapiclient."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gdrive_mcp.api import sheets as api


def _record(verb_chain) -> dict:
    """Capture kwargs passed to a chained sheet verb. `verb_chain` is a callable
    that returns the verb mock to monkey-patch."""
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
    def test_get_spreadsheet(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.get)
        api.get_spreadsheet(svc, spreadsheet_id="SS")
        assert captured["spreadsheetId"] == "SS"
        assert "properties" in captured["fields"]

    def test_get_values_kwargs(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.values.return_value.get)
        api.get_values(svc, spreadsheet_id="SS", range_="Sheet1!A1:B2", value_render="FORMULA")
        assert captured["spreadsheetId"] == "SS"
        assert captured["range"] == "Sheet1!A1:B2"
        assert captured["valueRenderOption"] == "FORMULA"
        assert captured["majorDimension"] == "ROWS"

    def test_batch_get_values(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.values.return_value.batchGet)
        api.batch_get_values(svc, spreadsheet_id="SS", ranges=["A1:B2", "C1:C3"])
        assert captured["ranges"] == ["A1:B2", "C1:C3"]


@pytest.mark.unit
class TestWriteValuesAPI:
    def test_update(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.values.return_value.update)
        api.update_values(svc, spreadsheet_id="SS", range_="Sheet1!A1", values=[[1, 2]])
        assert captured["range"] == "Sheet1!A1"
        assert captured["valueInputOption"] == "USER_ENTERED"
        assert captured["body"] == {"values": [[1, 2]]}

    def test_update_raw(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.values.return_value.update)
        api.update_values(svc, spreadsheet_id="SS", range_="A1", values=[[1]], value_input="RAW")
        assert captured["valueInputOption"] == "RAW"

    def test_append(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.values.return_value.append)
        api.append_values(svc, spreadsheet_id="SS", range_="A1", values=[["x"]])
        assert captured["insertDataOption"] == "INSERT_ROWS"

    def test_clear(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.values.return_value.clear)
        api.clear_values(svc, spreadsheet_id="SS", range_="A1:Z")
        assert captured["range"] == "A1:Z"
        assert captured["body"] == {}

    def test_batch_update_values(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.values.return_value.batchUpdate)
        api.batch_update_values(
            svc,
            spreadsheet_id="SS",
            data=[{"range": "A1", "values": [[1]]}],
            value_input="RAW",
        )
        assert captured["body"]["valueInputOption"] == "RAW"
        assert captured["body"]["data"] == [{"range": "A1", "values": [[1]]}]


@pytest.mark.unit
class TestStructureAPI:
    def test_batch_update_structure(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.batchUpdate)
        api.batch_update_structure(
            svc, spreadsheet_id="SS", requests=[{"addSheet": {"properties": {"title": "T"}}}]
        )
        assert captured["spreadsheetId"] == "SS"
        assert captured["body"]["requests"] == [{"addSheet": {"properties": {"title": "T"}}}]


@pytest.mark.unit
class TestFindReplaceAndDimensions:
    def test_find_replace_single_sheet(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.batchUpdate)
        api.find_replace(svc, spreadsheet_id="SS", find="x", replace="y", sheet_id=42)
        req = captured["body"]["requests"][0]["findReplace"]
        assert req["find"] == "x"
        assert req["replacement"] == "y"
        assert req["sheetId"] == 42
        assert "allSheets" not in req

    def test_find_replace_all_sheets(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.batchUpdate)
        api.find_replace(svc, spreadsheet_id="SS", find="x", replace="y")
        req = captured["body"]["requests"][0]["findReplace"]
        assert req["allSheets"] is True
        assert "sheetId" not in req

    def test_insert_dimension_rows(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.batchUpdate)
        api.insert_dimension(
            svc, spreadsheet_id="SS", sheet_id=0, dimension="ROWS",
            start_index=2, count=3,
        )
        rng = captured["body"]["requests"][0]["insertDimension"]["range"]
        assert rng == {"sheetId": 0, "dimension": "ROWS", "startIndex": 2, "endIndex": 5}

    def test_delete_dimension_cols(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.batchUpdate)
        api.delete_dimension(
            svc, spreadsheet_id="SS", sheet_id=0, dimension="COLUMNS",
            start_index=1, count=2,
        )
        rng = captured["body"]["requests"][0]["deleteDimension"]["range"]
        assert rng["dimension"] == "COLUMNS"
        assert (rng["startIndex"], rng["endIndex"]) == (1, 3)


@pytest.mark.unit
class TestSortAndFreeze:
    def test_sort_range_descending(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.batchUpdate)
        api.sort_range(
            svc, spreadsheet_id="SS", sheet_id=0,
            start_row_index=0, end_row_index=10,
            start_column_index=0, end_column_index=3,
            sort_column_index=1, descending=True,
        )
        req = captured["body"]["requests"][0]["sortRange"]
        assert req["range"]["startRowIndex"] == 0
        assert req["sortSpecs"][0] == {"dimensionIndex": 1, "sortOrder": "DESCENDING"}

    def test_freeze_sets_grid_props(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.batchUpdate)
        api.freeze(svc, spreadsheet_id="SS", sheet_id=5, rows=1, cols=2)
        req = captured["body"]["requests"][0]["updateSheetProperties"]
        assert req["properties"]["sheetId"] == 5
        assert req["properties"]["gridProperties"]["frozenRowCount"] == 1
        assert req["properties"]["gridProperties"]["frozenColumnCount"] == 2
        assert "frozenRowCount" in req["fields"]


@pytest.mark.unit
class TestMergeAndCopy:
    def test_merge_cells_default_type(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.batchUpdate)
        api.merge_cells(
            svc, spreadsheet_id="SS", sheet_id=0,
            start_row_index=0, end_row_index=2,
            start_column_index=0, end_column_index=3,
        )
        req = captured["body"]["requests"][0]["mergeCells"]
        assert req["mergeType"] == "MERGE_ALL"
        assert req["range"]["endRowIndex"] == 2

    def test_unmerge_cells(self):
        svc = MagicMock()
        captured = _record(lambda: svc.spreadsheets.return_value.batchUpdate)
        api.unmerge_cells(
            svc, spreadsheet_id="SS", sheet_id=0,
            start_row_index=0, end_row_index=2,
            start_column_index=0, end_column_index=3,
        )
        assert "unmergeCells" in captured["body"]["requests"][0]

    def test_copy_sheet_to(self):
        svc = MagicMock()
        captured: dict = {}

        def recorder(**kwargs):
            captured.update(kwargs)
            m = MagicMock()
            m.execute.return_value = {}
            return m

        svc.spreadsheets.return_value.sheets.return_value.copyTo.side_effect = recorder
        api.copy_sheet_to(
            svc, source_spreadsheet_id="SS1", source_sheet_id=42,
            destination_spreadsheet_id="SS2",
        )
        assert captured["spreadsheetId"] == "SS1"
        assert captured["sheetId"] == 42
        assert captured["body"] == {"destinationSpreadsheetId": "SS2"}


@pytest.mark.unit
class TestCreateViaDrive:
    def test_create_with_parent(self):
        drive = MagicMock()
        captured = _record(lambda: drive.files.return_value.create)
        api.create_via_drive(drive, title="MyData", parent_id="P")
        assert captured["body"] == {
            "name": "MyData",
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "parents": ["P"],
        }

    def test_create_no_parent(self):
        drive = MagicMock()
        captured = _record(lambda: drive.files.return_value.create)
        api.create_via_drive(drive, title="MyData")
        assert "parents" not in captured["body"]
