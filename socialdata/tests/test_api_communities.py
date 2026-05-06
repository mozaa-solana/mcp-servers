from __future__ import annotations

import pytest

from socialdata_mcp.api import communities as api
from socialdata_mcp.config import Config

CFG = Config(api_key="k", base_url="https://api.example.test", timeout_seconds=10.0)


@pytest.mark.asyncio
@pytest.mark.unit
class TestCommunitiesAPI:
    async def test_get_community(self, stub_request):
        stub_request.set({})
        await api.get_community(CFG, community_id="1")
        assert stub_request.last["path"] == "/twitter/community/1"

    async def test_community_tweets(self, stub_request):
        stub_request.set({})
        await api.get_community_tweets(CFG, community_id="1", sort="Top", cursor="C")
        assert stub_request.last["path"] == "/twitter/community/1/tweets"
        assert stub_request.last["params"] == {"type": "Top", "cursor": "C"}

    async def test_community_members(self, stub_request):
        stub_request.set({})
        await api.get_community_members(CFG, community_id="1")
        assert stub_request.last["path"] == "/twitter/community/1/members"

    async def test_community_search(self, stub_request):
        stub_request.set({})
        await api.search_community(CFG, community_id="1", query="ai", sort="Latest")
        assert stub_request.last["path"] == "/twitter/community/1/search"
        assert stub_request.last["params"] == {"query": "ai", "type": "Latest"}
