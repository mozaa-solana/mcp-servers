"""Tests for x_client.wrap_tweepy_error error mapping."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from xapi_mcp.x_client import XAPIError, wrap_tweepy_error


def _fake_tweepy_error(status: int, body: dict | None = None, messages: list | None = None):
    """Build something quacking like tweepy.HTTPException."""
    resp = SimpleNamespace(status_code=status, json=lambda: (body or {}), text="raw")
    err = Exception("fallback")
    err.response = resp  # type: ignore[attr-defined]
    if messages is not None:
        err.api_messages = messages  # type: ignore[attr-defined]
    return err


@pytest.mark.unit
class TestWrapTweepyError:
    def test_status_code_preserved(self):
        wrapped = wrap_tweepy_error(_fake_tweepy_error(403, {"detail": "forbidden"}))
        assert isinstance(wrapped, XAPIError)
        assert wrapped.status_code == 403
        assert wrapped.body == {"detail": "forbidden"}

    def test_429_rate_limit(self):
        wrapped = wrap_tweepy_error(_fake_tweepy_error(429))
        assert wrapped.status_code == 429

    def test_api_messages_used_when_available(self):
        err = _fake_tweepy_error(400, messages=["Duplicate post detected"])
        wrapped = wrap_tweepy_error(err)
        assert "Duplicate" in str(wrapped)

    def test_no_response_attribute(self):
        wrapped = wrap_tweepy_error(Exception("naked"))
        assert wrapped.status_code == 0
