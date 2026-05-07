"""Tests for user-related tools (lookup, follow, block + reverses)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from xapi_mcp.tools import users as tools
from tests.conftest import program_v2_response, set_dry_run


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetUser:
    async def test_by_handle_strips_at(self, fake_client):
        program_v2_response("get_user", fake_client,
                            {"id": "42", "username": "alice"})
        out = await tools.x_get_user("@alice")
        assert out["id"] == "42"
        kwargs = fake_client.v2.get_user.call_args.kwargs
        assert kwargs["username"] == "alice"

    async def test_by_numeric_id(self, fake_client):
        program_v2_response("get_user", fake_client,
                            {"id": "123", "username": "u"})
        out = await tools.x_get_user("123")
        assert out["id"] == "123"
        kwargs = fake_client.v2.get_user.call_args.kwargs
        assert kwargs["id"] == "123"


@pytest.mark.asyncio
@pytest.mark.unit
class TestFollow:
    async def test_resolves_handle_then_follows(self, fake_client):
        program_v2_response("get_user", fake_client, SimpleNamespace(id="42"))
        program_v2_response("follow_user", fake_client, {"following": True})
        out = await tools.x_follow_user("@alice")
        assert out["followed"] is True
        assert out["target_id"] == "42"
        fake_client.v2.follow_user.assert_called_once_with("42")

    async def test_numeric_id_skips_lookup(self, fake_client):
        program_v2_response("follow_user", fake_client, {})
        await tools.x_follow_user("99")
        fake_client.v2.get_user.assert_not_called()
        fake_client.v2.follow_user.assert_called_once_with("99")

    async def test_dry_run_blocks(self, monkeypatch, fake_client):
        set_dry_run(monkeypatch, True)
        out = await tools.x_follow_user("@alice")
        assert out["dry_run"] is True
        fake_client.v2.follow_user.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
class TestUnfollow:
    async def test_unfollows(self, fake_client):
        program_v2_response("unfollow_user", fake_client, {})
        out = await tools.x_unfollow_user("99")
        assert out["unfollowed"] is True
        fake_client.v2.unfollow_user.assert_called_once_with("99")


@pytest.mark.asyncio
@pytest.mark.unit
class TestBlockUnblock:
    async def test_block(self, fake_client):
        program_v2_response("block", fake_client, {})
        out = await tools.x_block_user("99")
        assert out["blocked"] is True

    async def test_unblock(self, fake_client):
        program_v2_response("unblock", fake_client, {})
        out = await tools.x_unblock_user("99")
        assert out["unblocked"] is True
