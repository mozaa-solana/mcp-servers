from __future__ import annotations

import pytest

from socialdata_mcp.api import search as api
from socialdata_mcp.config import Config

CFG = Config(api_key="k", base_url="https://api.example.test", timeout_seconds=10.0)


@pytest.mark.asyncio
@pytest.mark.unit
class TestSearchTweets:
    async def test_basic_call(self, stub_request):
        stub_request.set({"tweets": []})
        await api.search_tweets(CFG, query="AI", sort="Latest")

        call = stub_request.last
        assert call["method"] == "GET"
        assert call["path"] == "/twitter/search"
        assert call["params"] == {"query": "AI", "type": "Latest"}

    async def test_with_cursor(self, stub_request):
        stub_request.set({"tweets": []})
        await api.search_tweets(CFG, query="AI", sort="Top", cursor="abc")

        assert stub_request.last["params"] == {"query": "AI", "type": "Top", "cursor": "abc"}
