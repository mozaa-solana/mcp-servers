from __future__ import annotations

import pytest

from socialdata_mcp.tools import tweets as tools


TWEET = {
    "id_str": "1234567890",
    "user": {"screen_name": "alice"},
    "full_text": "hi",
}


@pytest.mark.asyncio
@pytest.mark.unit
class TestTwitterTweet:
    async def test_rejects_non_numeric(self, stub_request):
        out = await tools.twitter_tweet("not-a-number")
        assert out == {"error": "tweet_id must be a numeric string"}
        assert stub_request.last is None

    async def test_strips_whitespace(self, stub_request):
        stub_request.set(TWEET)
        await tools.twitter_tweet("  1234  ")
        assert stub_request.last["path"] == "/twitter/tweets/1234"

    async def test_returns_trimmed(self, stub_request):
        stub_request.set(TWEET)
        out = await tools.twitter_tweet("1234567890")
        assert out["id"] == "1234567890"


@pytest.mark.asyncio
@pytest.mark.unit
class TestTweetsLookup:
    async def test_rejects_empty(self, stub_request):
        out = await tools.twitter_tweets_lookup([])
        assert "non-empty" in out["error"]

    async def test_rejects_too_many(self, stub_request):
        out = await tools.twitter_tweets_lookup([str(i) for i in range(101)])
        assert "max 100" in out["error"]

    async def test_rejects_non_numeric(self, stub_request):
        out = await tools.twitter_tweets_lookup(["1", "abc"])
        assert "non-numeric" in out["error"]

    async def test_passes_ids(self, stub_request):
        stub_request.set({"tweets": [TWEET]})
        out = await tools.twitter_tweets_lookup(["1", "2"])
        assert stub_request.last["json"] == {"ids": ["1", "2"]}
        assert out["count"] == 1


@pytest.mark.asyncio
@pytest.mark.unit
class TestSubresources:
    @pytest.mark.parametrize(
        "fn_name,suffix",
        [
            ("twitter_tweet_comments", "/comments"),
            ("twitter_tweet_quotes", "/quotes"),
        ],
    )
    async def test_tweet_subresources(self, stub_request, fn_name, suffix):
        stub_request.set({"tweets": [TWEET]})
        fn = getattr(tools, fn_name)
        out = await fn("1234", cursor="C")
        assert stub_request.last["path"] == f"/twitter/tweets/1234{suffix}"
        assert stub_request.last["params"] == {"cursor": "C"}
        assert out["count"] == 1

    async def test_retweeters_returns_users(self, stub_request):
        stub_request.set({"users": [{"id_str": "1", "screen_name": "x"}]})
        out = await tools.twitter_tweet_retweeters("1234")
        assert out["users"][0]["screen_name"] == "x"

    async def test_thread_path(self, stub_request):
        stub_request.set({"tweets": [TWEET]})
        await tools.twitter_tweet_thread("9")
        assert stub_request.last["path"] == "/twitter/thread/9"

    async def test_thread_rejects_non_numeric(self, stub_request):
        out = await tools.twitter_tweet_thread("abc")
        assert "thread_id" in out["error"]

    async def test_article_attaches_field(self, stub_request):
        stub_request.set({"id_str": "9", "user": {"screen_name": "a"}, "article": {"title": "x"}})
        out = await tools.twitter_tweet_article("9")
        assert out["article"] == {"title": "x"}
