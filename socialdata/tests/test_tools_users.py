from __future__ import annotations

import pytest

from socialdata_mcp.tools import users as tools


USER = {"id_str": "44196397", "screen_name": "elonmusk", "name": "Elon"}
TWEET = {"id_str": "1", "user": {"screen_name": "elonmusk"}, "full_text": "hi"}


@pytest.mark.asyncio
@pytest.mark.unit
class TestUserInfo:
    async def test_trims_profile(self, stub_request):
        stub_request.set(USER)
        out = await tools.twitter_user_info("@elonmusk")
        assert out["screen_name"] == "elonmusk"
        assert out["url"] == "https://x.com/elonmusk"
        assert stub_request.last["path"] == "/twitter/user/elonmusk"


@pytest.mark.asyncio
@pytest.mark.unit
class TestUsersLookup:
    async def test_validates_empty(self, stub_request):
        out = await tools.twitter_users_lookup([])
        assert out == {"error": "ids must be a non-empty list"}
        assert stub_request.last is None

    async def test_validates_max_100(self, stub_request):
        out = await tools.twitter_users_lookup([str(i) for i in range(101)])
        assert "max 100" in out["error"]

    async def test_passes_ids_as_strings(self, stub_request):
        stub_request.set({"users": [USER]})
        out = await tools.twitter_users_lookup([1, 2, 3])
        assert stub_request.last["json"] == {"ids": ["1", "2", "3"]}
        assert out["count"] == 1


@pytest.mark.asyncio
@pytest.mark.unit
class TestUserTweets:
    async def test_includes_replies_flag_changes_path(self, stub_request):
        stub_request.set({"tweets": [TWEET]})
        await tools.twitter_user_tweets("42", include_replies=True)
        assert stub_request.last["path"] == "/twitter/user/42/tweets-and-replies"

    async def test_clamps_max_results(self, stub_request):
        stub_request.set({"tweets": [TWEET] * 100})
        out = await tools.twitter_user_tweets("42", max_results=999)
        assert out["count"] == 50


@pytest.mark.asyncio
@pytest.mark.unit
class TestFollowers:
    async def test_uses_verified_endpoint_when_flag_set(self, stub_request):
        stub_request.set({"users": [USER]})
        await tools.twitter_user_followers("42", verified_only=True)
        assert stub_request.last["path"] == "/twitter/user/42/verified-followers"

    async def test_uses_default_endpoint(self, stub_request):
        stub_request.set({"users": [USER]})
        await tools.twitter_user_followers("42")
        assert stub_request.last["path"] == "/twitter/followers/list"

    async def test_paginates(self, stub_request):
        stub_request.set({"users": [USER, USER], "next_cursor": "abc"})
        out = await tools.twitter_user_followers("42", max_results=1)
        assert out["count"] == 1
        assert out["next_cursor"] == "abc"


@pytest.mark.asyncio
@pytest.mark.unit
class TestUserMisc:
    async def test_extended_bio_passthrough(self, stub_request):
        stub_request.set({"text": "rich bio"})
        out = await tools.twitter_user_extended_bio("alice")
        assert out == {"text": "rich bio"}
        assert stub_request.last["path"] == "/twitter/user/alice/extended-bio"

    async def test_mentions_strips_at(self, stub_request):
        stub_request.set({"tweets": [TWEET]})
        await tools.twitter_user_mentions("@alice")
        assert stub_request.last["path"] == "/twitter/user/alice/mentions"
