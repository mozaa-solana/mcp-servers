from __future__ import annotations

import pytest

from socialdata_mcp.api import tweets as api
from socialdata_mcp.config import Config

CFG = Config(api_key="k", base_url="https://api.example.test", timeout_seconds=10.0)


@pytest.mark.asyncio
@pytest.mark.unit
class TestTweetsAPI:
    async def test_get_tweet_path(self, stub_request):
        stub_request.set({})
        await api.get_tweet(CFG, tweet_id="1234")
        assert stub_request.last["path"] == "/twitter/tweets/1234"

    async def test_get_tweets_by_ids_post(self, stub_request):
        stub_request.set({})
        await api.get_tweets_by_ids(CFG, ids=["1", 2])

        call = stub_request.last
        assert call["method"] == "POST"
        assert call["path"] == "/twitter/tweets-by-ids"
        assert call["json"] == {"ids": ["1", "2"]}

    async def test_subresources(self, stub_request):
        stub_request.set({})
        for fn, suffix in [
            (api.get_tweet_comments, "/comments"),
            (api.get_tweet_quotes, "/quotes"),
            (api.get_tweet_retweeters, "/retweeted_by"),
        ]:
            await fn(CFG, tweet_id="1234", cursor="C")
            assert stub_request.last["path"] == f"/twitter/tweets/1234{suffix}"
            assert stub_request.last["params"] == {"cursor": "C"}

    async def test_thread_and_article_paths(self, stub_request):
        stub_request.set({})

        await api.get_tweet_thread(CFG, thread_id="9")
        assert stub_request.last["path"] == "/twitter/thread/9"

        await api.get_tweet_article(CFG, article_id="42")
        assert stub_request.last["path"] == "/twitter/article/42"
