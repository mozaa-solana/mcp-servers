"""Tests for research / discovery tools."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from xapi_mcp.tools import research as tools
from tests.conftest import program_v2_response


@pytest.mark.asyncio
@pytest.mark.unit
class TestSearchRecent:
    async def test_returns_envelope(self, fake_client):
        fake_client.v2.search_recent_tweets.return_value = SimpleNamespace(
            data=[{"id": "1", "text": "hi"}],
            meta={"next_token": "ABC"},
        )
        out = await tools.x_search_recent_tweets("hello world", max_results=10)
        assert out["count"] == 1
        assert out["next_cursor"] == "ABC"
        assert out["estimated_cost_usd"] == round(0.005 * 10, 4)

    async def test_passes_cursor(self, fake_client):
        fake_client.v2.search_recent_tweets.return_value = SimpleNamespace(
            data=[], meta={}
        )
        await tools.x_search_recent_tweets("q", max_results=10, cursor="C1")
        kwargs = fake_client.v2.search_recent_tweets.call_args.kwargs
        assert kwargs["next_token"] == "C1"


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetUserRecentPosts:
    async def test_resolves_handle(self, fake_client):
        program_v2_response("get_user", fake_client, SimpleNamespace(id="42"))
        fake_client.v2.get_users_tweets.return_value = SimpleNamespace(
            data=[{"id": "1", "text": "x"}], meta={}
        )
        out = await tools.x_get_user_recent_posts("@alice", max_results=10)
        assert out["count"] == 1
        fake_client.v2.get_users_tweets.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetTrendingTopics:
    async def test_worldwide(self, fake_client):
        fake_client.v1.get_place_trends.return_value = [
            {"trends": [
                {"name": "#one", "url": "https://x.com/", "tweet_volume": 100},
                {"name": "#two", "url": "https://x.com/", "tweet_volume": None},
            ]}
        ]
        out = await tools.x_get_trending_topics(woeid=1)
        assert out["count"] == 2
        assert out["items"][0]["name"] == "#one"
        assert out["estimated_cost_usd"] == 0.0


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetUserFollowers:
    async def test_resolves_then_lists(self, fake_client):
        program_v2_response("get_user", fake_client, SimpleNamespace(id="42"))
        fake_client.v2.get_users_followers.return_value = SimpleNamespace(
            data=[{"id": "1", "username": "u1"}], meta={}
        )
        out = await tools.x_get_user_followers("@alice", max_results=100)
        assert out["count"] == 1
        assert out["estimated_cost_usd"] == round(0.005 * 100, 4)
