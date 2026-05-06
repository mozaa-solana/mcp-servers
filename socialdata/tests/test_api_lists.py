from __future__ import annotations

import pytest

from socialdata_mcp.api import lists as api
from socialdata_mcp.config import Config

CFG = Config(api_key="k", base_url="https://api.example.test", timeout_seconds=10.0)


@pytest.mark.asyncio
@pytest.mark.unit
class TestListsAPI:
    async def test_get_list(self, stub_request):
        stub_request.set({})
        await api.get_list(CFG, list_id="123")
        assert stub_request.last["path"] == "/twitter/lists/show"
        assert stub_request.last["params"] == {"id": "123"}

    async def test_get_list_members(self, stub_request):
        stub_request.set({})
        await api.get_list_members(CFG, list_id="123", cursor="C")
        assert stub_request.last["path"] == "/twitter/lists/members"
        assert stub_request.last["params"] == {"list_id": "123", "cursor": "C"}

    async def test_get_list_tweets(self, stub_request):
        stub_request.set({})
        await api.get_list_tweets(CFG, list_id="123")
        assert stub_request.last["path"] == "/twitter/list/123/tweets"
        assert stub_request.last["params"] is None
