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
