"""Tests for analytics tools."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from xapi_mcp.tools import analytics as tools
from tests.conftest import program_v2_response


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetTweetMetrics:
    async def test_returns_all_metric_blocks(self, fake_client):
        program_v2_response("get_tweet", fake_client, {
            "id": "1", "text": "hi", "author_id": "42",
            "public_metrics": {"like_count": 5},
            "non_public_metrics": {"impression_count": 100},
            "organic_metrics": {"url_link_clicks": 3},
        })
        out = await tools.x_get_tweet_metrics("1")
        assert out["public_metrics"]["like_count"] == 5
        assert out["non_public_metrics"]["impression_count"] == 100
        assert out["organic_metrics"]["url_link_clicks"] == 3
        assert out["estimated_cost_usd"] == 0.001


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetLikingUsers:
    async def test_lists(self, fake_client):
        fake_client.v2.get_liking_users.return_value = SimpleNamespace(
            data=[{"id": "1", "username": "u1"}, {"id": "2", "username": "u2"}],
            meta={},
        )
        out = await tools.x_get_liking_users("123", max_results=100)
        assert out["count"] == 2
        assert out["estimated_cost_usd"] == round(0.005 * 100, 4)


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetRetweeters:
    async def test_lists(self, fake_client):
        fake_client.v2.get_retweeters.return_value = SimpleNamespace(
            data=[{"id": "1", "username": "u1"}], meta={},
        )
        out = await tools.x_get_retweeters("123", max_results=100)
        assert out["count"] == 1


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetQuoteTweets:
    async def test_lists(self, fake_client):
        fake_client.v2.get_quote_tweets.return_value = SimpleNamespace(
            data=[{"id": "1", "text": "@you nice"}], meta={},
        )
        out = await tools.x_get_quote_tweets("123", max_results=10)
        assert out["count"] == 1
        assert out["estimated_cost_usd"] == round(0.005 * 10, 4)


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetReplies:
    async def test_uses_conversation_id_query(self, fake_client):
        fake_client.v2.search_recent_tweets.return_value = SimpleNamespace(
            data=[{"id": "9", "text": "a reply"}], meta={},
        )
        out = await tools.x_get_replies("123", max_results=10)
        assert out["count"] == 1
        kwargs = fake_client.v2.search_recent_tweets.call_args.kwargs
        assert "conversation_id:123" in kwargs["query"]
