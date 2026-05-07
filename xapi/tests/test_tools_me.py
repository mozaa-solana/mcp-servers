"""Tests for me-related tools (cheap owned-reads)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from xapi_mcp.tools import me as tools
from tests.conftest import program_v2_response


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetMe:
    async def test_returns_trimmed_user(self, fake_client):
        program_v2_response("get_me", fake_client,
                            {"id": "42", "username": "alice", "name": "Alice"})
        out = await tools.x_get_me()
        assert out["id"] == "42"
        assert out["username"] == "alice"
        assert out["estimated_cost_usd"] == 0.001  # owned-read tier

    async def test_records_cost(self, fake_client, patched):
        program_v2_response("get_me", fake_client, {"id": "1", "username": "u"})
        await tools.x_get_me()
        assert patched.budget.snapshot()["spent_usd"] == 0.001


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetMyRecentPosts:
    async def test_returns_paginated_envelope(self, fake_client):
        program_v2_response("get_me", fake_client, SimpleNamespace(id="42"))
        # get_users_tweets returns ResultSet — emulate with .data list + .meta.
        fake_client.v2.get_users_tweets.return_value = SimpleNamespace(
            data=[{"id": "1", "text": "a"}, {"id": "2", "text": "b"}],
            meta={"next_token": "ZZZ"},
        )
        out = await tools.x_get_my_recent_posts(max_results=10)
        assert out["count"] == 2
        assert out["next_cursor"] == "ZZZ"
        assert out["estimated_cost_usd"] == round(0.001 * 10, 4)

    async def test_clamps_max_results(self, fake_client):
        program_v2_response("get_me", fake_client, SimpleNamespace(id="42"))
        fake_client.v2.get_users_tweets.return_value = SimpleNamespace(
            data=[], meta={}
        )
        await tools.x_get_my_recent_posts(max_results=999)
        # Tweepy was called with max_results clamped to 100.
        kwargs = fake_client.v2.get_users_tweets.call_args.kwargs
        assert kwargs["max_results"] == 100

    async def test_clamps_below_minimum(self, fake_client):
        program_v2_response("get_me", fake_client, SimpleNamespace(id="42"))
        fake_client.v2.get_users_tweets.return_value = SimpleNamespace(data=[], meta={})
        await tools.x_get_my_recent_posts(max_results=1)
        kwargs = fake_client.v2.get_users_tweets.call_args.kwargs
        assert kwargs["max_results"] == 5
