from __future__ import annotations

import pytest

from socialdata_mcp.api import social_actions as social_api
from socialdata_mcp.api import spaces as spaces_api
from socialdata_mcp.config import Config

CFG = Config(api_key="k", base_url="https://api.example.test", timeout_seconds=10.0)


@pytest.mark.asyncio
@pytest.mark.unit
class TestSpacesAPI:
    async def test_get_space(self, stub_request):
        stub_request.set({})
        await spaces_api.get_space(CFG, space_id="abc")
        assert stub_request.last["path"] == "/twitter/space/abc"


@pytest.mark.asyncio
@pytest.mark.unit
class TestSocialActionsAPI:
    async def test_verify_following(self, stub_request):
        stub_request.set({})
        await social_api.verify_following(CFG, source_user_id="1", target_user_id="2")
        assert stub_request.last["path"] == "/twitter/user/1/following/2"

    async def test_verify_retweeted(self, stub_request):
        stub_request.set({})
        await social_api.verify_retweeted(CFG, tweet_id="9", user_id="1")
        assert stub_request.last["path"] == "/twitter/tweets/9/retweeted_by/1"

    async def test_verify_commented(self, stub_request):
        stub_request.set({})
        await social_api.verify_commented(CFG, tweet_id="9", user_id="1")
        assert stub_request.last["path"] == "/twitter/tweets/9/commented_by/1"
