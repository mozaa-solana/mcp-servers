"""Tests for api/drives.py."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gdrive_mcp.api import drives as api


@pytest.mark.unit
class TestDrivesAPI:
    def test_list_drives_basic(self):
        svc = MagicMock()
        captured: dict = {}

        def recorder(**kwargs):
            captured.update(kwargs)
            m = MagicMock()
            m.execute.return_value = {"drives": []}
            return m

        svc.drives.return_value.list.side_effect = recorder
        api.list_drives(svc, page_size=20)
        assert captured["pageSize"] == 20
        assert "id,name" in captured["fields"]
        assert "pageToken" not in captured

    def test_list_drives_with_cursor(self):
        svc = MagicMock()
        captured: dict = {}

        def recorder(**kwargs):
            captured.update(kwargs)
            m = MagicMock()
            m.execute.return_value = {}
            return m

        svc.drives.return_value.list.side_effect = recorder
        api.list_drives(svc, page_token="C")
        assert captured["pageToken"] == "C"
