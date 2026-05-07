"""Tests for bookmark tools."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from xapi_mcp.tools import bookmarks as tools
from tests.conftest import program_v2_response


@pytest.mark.asyncio
@pytest.mark.unit
class TestBookmark:
    async def test_add(self, fake_client):
        program_v2_response("bookmark", fake_client, {"bookmarked": True})
        out = await tools.x_bookmark_tweet("123")
        assert out["bookmarked"] is True
        assert out["estimated_cost_usd"] == 0.015

    async def test_remove(self, fake_client):
        program_v2_response("remove_bookmark", fake_client, {})
        out = await tools.x_remove_bookmark("123")
        assert out["removed"] is True
        # Owned-tier read pricing for removal.
        assert out["estimated_cost_usd"] == 0.001

    async def test_list(self, fake_client):
        fake_client.v2.get_bookmarks.return_value = SimpleNamespace(
            data=[{"id": "1", "text": "a"}, {"id": "2", "text": "b"}],
            meta={"next_token": "ZZZ"},
        )
        out = await tools.x_get_my_bookmarks(max_results=10)
        assert out["count"] == 2
        assert out["next_cursor"] == "ZZZ"
        assert out["estimated_cost_usd"] == round(0.001 * 10, 4)
