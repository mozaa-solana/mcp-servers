"""Smoke tests for lists/communities/spaces/social-actions tool layer."""
from __future__ import annotations

import pytest

from socialdata_mcp.tools import (
    communities as communities_tools,
    lists as lists_tools,
    social_actions as social_tools,
    spaces as spaces_tools,
)


TWEET = {"id_str": "1", "user": {"screen_name": "x"}, "full_text": "hi"}
USER = {"id_str": "1", "screen_name": "alice"}


@pytest.mark.asyncio
@pytest.mark.unit
class TestListsTools:
    async def test_list_info(self, stub_request):
        stub_request.set({"name": "My List"})
        out = await lists_tools.twitter_list_info("123")
        assert out == {"name": "My List"}
        assert stub_request.last["params"] == {"id": "123"}

    async def test_list_members(self, stub_request):
        stub_request.set({"users": [USER]})
        out = await lists_tools.twitter_list_members("123", max_results=1)
        assert out["count"] == 1

    async def test_list_tweets(self, stub_request):
        stub_request.set({"tweets": [TWEET, TWEET]})
        out = await lists_tools.twitter_list_tweets("123", max_results=1)
        assert out["count"] == 1


@pytest.mark.asyncio
@pytest.mark.unit
class TestCommunitiesTools:
    async def test_info(self, stub_request):
        stub_request.set({"name": "C"})
        out = await communities_tools.twitter_community_info("9")
        assert out == {"name": "C"}

    async def test_tweets_normalizes_sort(self, stub_request):
        stub_request.set({"tweets": [TWEET]})
        out = await communities_tools.twitter_community_tweets("9", sort="top")
        assert stub_request.last["params"]["type"] == "Top"
        assert out["sort"] == "Top"

    async def test_members(self, stub_request):
        stub_request.set({"users": [USER]})
        out = await communities_tools.twitter_community_members("9")
        assert out["users"][0]["screen_name"] == "alice"

    async def test_search(self, stub_request):
        stub_request.set({"tweets": [TWEET]})
        out = await communities_tools.twitter_community_search("9", "ai")
        assert stub_request.last["params"] == {"query": "ai", "type": "Latest"}
        assert out["query"] == "ai"


@pytest.mark.asyncio
@pytest.mark.unit
class TestSpacesTools:
    async def test_space_info(self, stub_request):
        stub_request.set({"id": "abc"})
        out = await spaces_tools.twitter_space_info("abc")
        assert out == {"id": "abc"}
        assert stub_request.last["path"] == "/twitter/space/abc"


@pytest.mark.asyncio
@pytest.mark.unit
class TestSocialActions:
    async def test_verify_following(self, stub_request):
        stub_request.set({"is_following": True})
        out = await social_tools.twitter_verify_following("1", "2")
        assert out == {"is_following": True}

    async def test_verify_retweeted(self, stub_request):
        stub_request.set({"is_retweeted": False})
        out = await social_tools.twitter_verify_retweeted("9", "1")
        assert out == {"is_retweeted": False}

    async def test_verify_commented(self, stub_request):
        stub_request.set({"is_commented": True})
        out = await social_tools.twitter_verify_commented("9", "1")
        assert out == {"is_commented": True}
