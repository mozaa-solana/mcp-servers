"""Tests for post-related tools (create/delete/like/retweet + reverses)."""
from __future__ import annotations

import pytest

from xapi_mcp.tools import posts as tools
from tests.conftest import program_v2_response, set_budget, set_dry_run


@pytest.mark.asyncio
@pytest.mark.unit
class TestPostTweet:
    async def test_creates_plain(self, fake_client):
        program_v2_response("create_tweet", fake_client,
                            {"id": "100", "text": "hello"})
        out = await tools.x_post_tweet("hello")
        assert out["id"] == "100"
        assert out["estimated_cost_usd"] == 0.015

    async def test_url_triggers_link_tax(self, fake_client):
        program_v2_response("create_tweet", fake_client,
                            {"id": "101", "text": "see https://x.com"})
        out = await tools.x_post_tweet("see https://x.com")
        assert out["estimated_cost_usd"] == 0.20

    async def test_empty_text_rejected(self, fake_client):
        out = await tools.x_post_tweet("")
        assert "text must not be empty" in out["error"]
        fake_client.v2.create_tweet.assert_not_called()

    async def test_whitespace_only_rejected(self, fake_client):
        out = await tools.x_post_tweet("   \n\t")
        assert "text must not be empty" in out["error"]

    async def test_passes_reply_and_quote(self, fake_client):
        program_v2_response("create_tweet", fake_client, {"id": "1"})
        await tools.x_post_tweet("hi", reply_to_tweet_id="9", quote_tweet_id="8")
        kwargs = fake_client.v2.create_tweet.call_args.kwargs
        assert kwargs["in_reply_to_tweet_id"] == "9"
        assert kwargs["quote_tweet_id"] == "8"

    async def test_passes_media_ids(self, fake_client):
        program_v2_response("create_tweet", fake_client, {"id": "1"})
        await tools.x_post_tweet("hi", media_ids=["m1", "m2"])
        kwargs = fake_client.v2.create_tweet.call_args.kwargs
        assert kwargs["media_ids"] == ["m1", "m2"]

    async def test_dry_run_short_circuits(self, monkeypatch, fake_client):
        set_dry_run(monkeypatch, True)
        out = await tools.x_post_tweet("hello")
        assert out["dry_run"] is True
        assert out["would_post"] == "hello"
        fake_client.v2.create_tweet.assert_not_called()

    async def test_budget_blocks_call(self, monkeypatch, fake_client):
        set_budget(monkeypatch, 0.001)  # cap below plain post cost
        out = await tools.x_post_tweet("hello")
        assert out.get("violation") == "budget"
        fake_client.v2.create_tweet.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
class TestEngagement:
    async def test_like(self, fake_client):
        program_v2_response("like", fake_client, {"liked": True})
        out = await tools.x_like_tweet("123")
        assert out["liked"] is True
        assert out["id"] == "123"
        fake_client.v2.like.assert_called_once_with("123")

    async def test_unlike(self, fake_client):
        program_v2_response("unlike", fake_client, {})
        out = await tools.x_unlike_tweet("123")
        assert out["unliked"] is True

    async def test_retweet(self, fake_client):
        program_v2_response("retweet", fake_client, {})
        out = await tools.x_retweet("123")
        assert out["retweeted"] is True

    async def test_unretweet(self, fake_client):
        program_v2_response("unretweet", fake_client, {})
        out = await tools.x_unretweet("123")
        assert out["unretweeted"] is True

    async def test_dry_run_blocks(self, monkeypatch, fake_client):
        set_dry_run(monkeypatch, True)
        out = await tools.x_like_tweet("123")
        assert out["dry_run"] is True
        fake_client.v2.like.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
class TestDeleteTweet:
    async def test_deletes(self, fake_client):
        program_v2_response("delete_tweet", fake_client, {"deleted": True})
        out = await tools.x_delete_tweet("123")
        assert out["deleted"] is True
        assert out["id"] == "123"
        fake_client.v2.delete_tweet.assert_called_once_with("123")


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetTweet:
    async def test_lookup(self, fake_client):
        program_v2_response("get_tweet", fake_client,
                            {"id": "9", "text": "looked up"})
        out = await tools.x_get_tweet("9")
        assert out["text"] == "looked up"
        assert out["estimated_cost_usd"] == 0.005
