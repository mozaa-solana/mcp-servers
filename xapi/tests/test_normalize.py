"""Tests for normalize.trim_tweet / trim_user / paginated."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from xapi_mcp.normalize import paginated, trim_tweet, trim_user


@pytest.mark.unit
class TestTrimTweet:
    def test_keeps_known_fields(self):
        raw = {
            "id": "1",
            "text": "hi",
            "created_at": "2026-01-01T00:00:00Z",
            "author_id": "42",
            "noise": "drop me",
            "context_annotations": ["junk"],
        }
        out = trim_tweet(raw)
        assert out == {
            "id": "1",
            "text": "hi",
            "created_at": "2026-01-01T00:00:00Z",
            "author_id": "42",
        }

    def test_handles_simplenamespace(self):
        # Tweepy returns objects with .data dict.
        raw = SimpleNamespace(data={"id": "1", "text": "hi"})
        out = trim_tweet(raw)
        assert out == {"id": "1", "text": "hi"}

    def test_none_safe(self):
        assert trim_tweet(None) == {}


@pytest.mark.unit
class TestTrimUser:
    def test_keeps_known_fields(self):
        raw = {"id": "1", "username": "alice", "name": "Alice", "verified": True,
               "drop_me": True}
        out = trim_user(raw)
        assert out == {"id": "1", "username": "alice", "name": "Alice", "verified": True}


@pytest.mark.unit
class TestPaginated:
    def test_envelope_shape(self):
        items = [{"id": "1", "text": "a"}, {"id": "2", "text": "b"}]
        out = paginated(items, "cursor-xyz", trim_tweet)
        assert out["count"] == 2
        assert out["next_cursor"] == "cursor-xyz"
        assert out["items"][0] == {"id": "1", "text": "a"}

    def test_empty_list(self):
        out = paginated([], None, trim_tweet)
        assert out == {"count": 0, "items": [], "next_cursor": None}
