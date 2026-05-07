"""Tests for api/files.py — verify the verbs and kwargs we send to googleapiclient."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gdrive_mcp.api import files as api


def _record_call(svc: MagicMock, verb: str) -> dict:
    """Capture kwargs passed to svc.files().<verb>(...)."""
    captured: dict = {}

    def recorder(**kwargs):
        captured.update(kwargs)
        m = MagicMock()
        m.execute.return_value = {}
        return m

    getattr(svc.files.return_value, verb).side_effect = recorder
    return captured


@pytest.mark.unit
class TestFilesAPI:
    def test_list_includes_shared_drive_kwargs(self):
        svc = MagicMock()
        captured = _record_call(svc, "list")
        api.list_files(svc, q="x", page_size=10, page_token="C")
        assert captured["q"] == "x"
        assert captured["pageSize"] == 10
        assert captured["pageToken"] == "C"
        assert captured["supportsAllDrives"] is True
        assert captured["includeItemsFromAllDrives"] is True

    def test_list_omits_q_when_blank(self):
        svc = MagicMock()
        captured = _record_call(svc, "list")
        api.list_files(svc)
        assert "q" not in captured

    def test_get_metadata(self):
        svc = MagicMock()
        captured = _record_call(svc, "get")
        api.get_metadata(svc, file_id="abc")
        assert captured["fileId"] == "abc"
        assert "id," in captured["fields"]

    def test_create_folder_sets_mime(self):
        svc = MagicMock()
        captured = _record_call(svc, "create")
        api.create_folder(svc, name="n", parent_id="P")
        assert captured["body"]["mimeType"] == "application/vnd.google-apps.folder"
        assert captured["body"]["parents"] == ["P"]

    def test_create_folder_no_parent(self):
        svc = MagicMock()
        captured = _record_call(svc, "create")
        api.create_folder(svc, name="n")
        assert "parents" not in captured["body"]

    def test_rename(self):
        svc = MagicMock()
        captured = _record_call(svc, "update")
        api.rename(svc, file_id="F", new_name="NEW")
        assert captured["fileId"] == "F"
        assert captured["body"] == {"name": "NEW"}

    def test_move_recomputes_old_parents(self):
        svc = MagicMock()
        # First call (get) returns current parents
        svc.files.return_value.get.return_value.execute.return_value = {
            "parents": ["OLD1", "OLD2"]
        }
        captured = _record_call(svc, "update")
        api.move(svc, file_id="F", new_parent_id="NEW")
        assert captured["addParents"] == "NEW"
        assert captured["removeParents"] == "OLD1,OLD2"

    def test_trash_sets_flag(self):
        svc = MagicMock()
        captured = _record_call(svc, "update")
        api.trash(svc, file_id="F")
        assert captured["body"] == {"trashed": True}

    def test_untrash_sets_flag(self):
        svc = MagicMock()
        captured = _record_call(svc, "update")
        api.untrash(svc, file_id="F")
        assert captured["body"] == {"trashed": False}

    def test_copy_with_name_and_parent(self):
        svc = MagicMock()
        captured = _record_call(svc, "copy")
        api.copy_file(svc, file_id="F", name="copy.txt", parent_id="P")
        assert captured["fileId"] == "F"
        assert captured["body"] == {"name": "copy.txt", "parents": ["P"]}

    def test_copy_minimal(self):
        svc = MagicMock()
        captured = _record_call(svc, "copy")
        api.copy_file(svc, file_id="F")
        assert captured["body"] == {}
