"""Integration-style tests for handle_x_errors decorator behavior."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from xapi_mcp.tools import me as tools_me
from xapi_mcp.tools import posts as tools_posts


def _tweepy_error(status: int, body: dict | None = None):
    """Build something that quacks like a tweepy.errors.TweepyException subclass."""
    try:
        from tweepy.errors import TweepyException
    except Exception:  # pragma: no cover
        TweepyException = Exception

    class FakeErr(TweepyException):
        pass

    err = FakeErr(f"status {status}")
    err.response = SimpleNamespace(  # type: ignore[attr-defined]
        status_code=status,
        json=lambda: body or {},
        text="raw",
    )
    return err


@pytest.mark.asyncio
@pytest.mark.unit
class TestHandleXErrorsDecorator:
    async def test_tweepy_403_becomes_dict(self, fake_client):
        fake_client.v2.get_me.side_effect = _tweepy_error(403, {"detail": "forbidden"})
        out = await tools_me.x_get_me()
        assert "error" in out
        assert out["status_code"] == 403

    async def test_tweepy_429_rate_limit(self, fake_client):
        fake_client.v2.create_tweet.side_effect = _tweepy_error(429)
        out = await tools_posts.x_post_tweet("hi")
        assert out["status_code"] == 429
