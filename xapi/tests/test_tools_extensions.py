"""Tests for extensions to existing tool modules:
- posts.x_pin_tweet / x_unpin_tweet
- users.x_mute_user / x_unmute_user
- me.x_get_my_followers / x_get_my_following
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from xapi_mcp.tools import me as tools_me
from xapi_mcp.tools import posts as tools_posts
from xapi_mcp.tools import users as tools_users
from tests.conftest import program_v2_response, set_dry_run


@pytest.mark.asyncio
@pytest.mark.unit
class TestPinUnpin:
    async def test_pin_uses_native_method_when_present(self, fake_client):
        # Tweepy ≥ 4.x has client.pin_tweet
        fake_client.v2.pin_tweet = lambda *_a, **_k: SimpleNamespace(
            data={"pinned": True}
        )
        out = await tools_posts.x_pin_tweet("123")
        assert out["pinned"] is True
        assert out["id"] == "123"

    async def test_unpin(self, fake_client):
        fake_client.v2.unpin_tweet = lambda *_a, **_k: SimpleNamespace(
            data={"pinned": False}
        )
        out = await tools_posts.x_unpin_tweet("123")
        assert out["unpinned"] is True

    async def test_dry_run(self, monkeypatch, fake_client):
        set_dry_run(monkeypatch, True)
        out = await tools_posts.x_pin_tweet("123")
        assert out["dry_run"] is True


@pytest.mark.asyncio
@pytest.mark.unit
class TestMuteUnmute:
    async def test_mute(self, fake_client):
        program_v2_response("mute", fake_client, {})
        program_v2_response("get_user", fake_client, SimpleNamespace(id="42"))
        out = await tools_users.x_mute_user("@alice")
        assert out["muted"] is True
        assert out["target_id"] == "42"

    async def test_unmute(self, fake_client):
        program_v2_response("unmute", fake_client, {})
        out = await tools_users.x_unmute_user("99")
        assert out["unmuted"] is True
        fake_client.v2.unmute.assert_called_once_with("99")


@pytest.mark.asyncio
@pytest.mark.unit
class TestMyFollowersFollowing:
    async def test_my_followers(self, fake_client):
        program_v2_response("get_me", fake_client, SimpleNamespace(id="42"))
        fake_client.v2.get_users_followers.return_value = SimpleNamespace(
            data=[{"id": "1", "username": "f1"}], meta={"next_token": "X"},
        )
        out = await tools_me.x_get_my_followers(max_results=100)
        assert out["count"] == 1
        assert out["next_cursor"] == "X"
        # Owned-tier pricing.
        assert out["estimated_cost_usd"] == round(0.001 * 100, 4)

    async def test_my_following(self, fake_client):
        program_v2_response("get_me", fake_client, SimpleNamespace(id="42"))
        fake_client.v2.get_users_following.return_value = SimpleNamespace(
            data=[{"id": "1", "username": "f1"}], meta={},
        )
        out = await tools_me.x_get_my_following(max_results=100)
        assert out["count"] == 1
