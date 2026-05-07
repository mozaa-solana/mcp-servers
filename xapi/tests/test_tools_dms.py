"""Tests for DM tools."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from xapi_mcp.tools import dms as tools
from tests.conftest import program_v2_response, set_dry_run


@pytest.mark.asyncio
@pytest.mark.unit
class TestSendDM:
    async def test_sends_after_resolving_handle(self, fake_client):
        program_v2_response("get_user", fake_client, SimpleNamespace(id="42"))
        program_v2_response("create_direct_message", fake_client, {"event_id": "X"})
        out = await tools.x_send_dm("@alice", "hi")
        assert out["sent"] is True
        assert out["target_id"] == "42"

    async def test_empty_text_rejected(self, fake_client):
        out = await tools.x_send_dm("@alice", "")
        assert "text must not be empty" in out["error"]
        fake_client.v2.create_direct_message.assert_not_called()

    async def test_dry_run(self, monkeypatch, fake_client):
        set_dry_run(monkeypatch, True)
        out = await tools.x_send_dm("@alice", "hi")
        assert out["dry_run"] is True
        fake_client.v2.create_direct_message.assert_not_called()
