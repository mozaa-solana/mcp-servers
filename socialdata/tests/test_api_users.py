from __future__ import annotations

import pytest

from socialdata_mcp.api import users as api
from socialdata_mcp.config import Config

CFG = Config(api_key="k", base_url="https://api.example.test", timeout_seconds=10.0)


@pytest.mark.asyncio
@pytest.mark.unit
class TestUsersAPI:
    async def test_get_user_strips_at(self, stub_request):
        stub_request.set({})
        await api.get_user(CFG, handle_or_id="@elonmusk")
        assert stub_request.last["path"] == "/twitter/user/elonmusk"

    async def test_get_users_by_ids_post_json(self, stub_request):
        stub_request.set({"users": []})
        await api.get_users_by_ids(CFG, ids=[1, "2", 3])

        call = stub_request.last
        assert call["method"] == "POST"
        assert call["path"] == "/twitter/users-by-id"
        assert call["json"] == {"ids": ["1", "2", "3"]}

    async def test_followers(self, stub_request):
        stub_request.set({})
        await api.get_user_followers(CFG, user_id="42", cursor="C")

        call = stub_request.last
        assert call["path"] == "/twitter/followers/list"
        assert call["params"] == {"user_id": "42", "cursor": "C"}

    async def test_verified_followers(self, stub_request):
        stub_request.set({})
        await api.get_user_verified_followers(CFG, user_id="42")
        assert stub_request.last["path"] == "/twitter/user/42/verified-followers"
        assert stub_request.last["params"] is None

    async def test_followings(self, stub_request):
        stub_request.set({})
        await api.get_user_followings(CFG, user_id="42")
        assert stub_request.last["path"] == "/twitter/friends/list"
        assert stub_request.last["params"] == {"user_id": "42"}

    async def test_user_tweets_replies_toggle(self, stub_request):
        stub_request.set({})

        await api.get_user_tweets(CFG, user_id="42")
        assert stub_request.last["path"].endswith("/tweets")

        await api.get_user_tweets(CFG, user_id="42", include_replies=True)
        assert stub_request.last["path"].endswith("/tweets-and-replies")

    async def test_mentions(self, stub_request):
        stub_request.set({})
        await api.get_user_mentions(CFG, screen_name="@alice", cursor="C")
        assert stub_request.last["path"] == "/twitter/user/alice/mentions"
        assert stub_request.last["params"] == {"cursor": "C"}

    async def test_highlights_affiliates_lists_similar_paths(self, stub_request):
        stub_request.set({})
        for fn, suffix in [
            (api.get_user_highlights, "/highlights"),
            (api.get_user_affiliates, "/affiliates"),
            (api.get_user_lists, "/lists"),
            (api.get_user_similar, "/similar"),
        ]:
            await fn(CFG, user_id="42")
            assert stub_request.last["path"] == f"/twitter/user/42{suffix}"

    async def test_extended_bio(self, stub_request):
        stub_request.set({})
        await api.get_user_extended_bio(CFG, screen_name="alice")
        assert stub_request.last["path"] == "/twitter/user/alice/extended-bio"
