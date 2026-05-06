"""Tests for pure normalization helpers."""
from __future__ import annotations

import pytest

from socialdata_mcp.normalize import (
    clamp,
    extract_items,
    paginated,
    trim_tweet,
    trim_user,
)


SAMPLE_TWEET = {
    "id_str": "1234567890",
    "tweet_created_at": "Wed Jan 15 12:00:00 +0000 2026",
    "full_text": "Hello world from X",
    "lang": "en",
    "retweet_count": 5,
    "favorite_count": 42,
    "reply_count": 3,
    "quote_count": 1,
    "views_count": 1000,
    "user": {
        "screen_name": "elonmusk",
        "name": "Elon Musk",
        "blue_verified": True,
        "followers_count": 200_000_000,
    },
}


@pytest.mark.unit
class TestTrimTweet:
    def test_extracts_canonical_fields(self):
        out = trim_tweet(SAMPLE_TWEET)
        assert out["id"] == "1234567890"
        assert out["text"] == "Hello world from X"
        assert out["url"] == "https://x.com/elonmusk/status/1234567890"
        assert out["author"]["verified"] is True
        assert out["is_retweet"] is False
        assert out["is_quote"] is False

    def test_falls_back_to_id_and_text_keys(self):
        tw = {"id": 99, "text": "fallback", "user": {"screen_name": "alice"}}
        out = trim_tweet(tw)
        assert out["id"] == 99
        assert out["text"] == "fallback"
        assert out["url"] == "https://x.com/alice/status/99"

    def test_url_none_when_screen_name_missing(self):
        assert trim_tweet({"id_str": "1", "user": {}})["url"] is None

    def test_flags_retweet_and_quote(self):
        out = trim_tweet(
            {
                "id_str": "1",
                "user": {"screen_name": "x"},
                "retweeted_status": {"id": 2},
                "quoted_status_result": {"id": 3},
            }
        )
        assert out["is_retweet"] is True
        assert out["is_quote"] is True

    def test_handles_none_input(self):
        out = trim_tweet(None)
        assert out["id"] is None
        assert out["author"]["screen_name"] is None


@pytest.mark.unit
class TestTrimUser:
    def test_maps_canonical_fields(self):
        out = trim_user(
            {
                "id_str": "44196397",
                "screen_name": "elonmusk",
                "name": "Elon",
                "description": "bio",
                "blue_verified": True,
                "followers_count": 100,
                "following_count": 5,
                "tweet_count": 999,
                "user_created_at": "2009-06-02",
            }
        )
        assert out["id"] == "44196397"
        assert out["url"] == "https://x.com/elonmusk"
        assert out["friends_count"] == 5
        assert out["statuses_count"] == 999
        assert out["created_at"] == "2009-06-02"

    def test_url_none_when_handle_missing(self):
        assert trim_user({"name": "anon"})["url"] is None


@pytest.mark.unit
class TestHelpers:
    @pytest.mark.parametrize(
        "raw,lo,hi,expected",
        [
            (5, 1, 10, 5),
            (-3, 1, 10, 1),
            (999, 1, 50, 50),
            ("abc", 1, 5, 1),
            (None, 0, 10, 0),
        ],
    )
    def test_clamp(self, raw, lo, hi, expected):
        assert clamp(raw, lo, hi) == expected

    def test_extract_items_picks_first_present(self):
        assert extract_items({"data": [1, 2]}, "tweets", "data") == [1, 2]

    def test_extract_items_returns_empty_when_missing(self):
        assert extract_items({"meta": "x"}, "tweets", "data") == []

    def test_extract_items_ignores_non_list(self):
        assert extract_items({"tweets": "not a list", "data": [1]}, "tweets", "data") == [1]

    def test_paginated_envelope(self):
        out = paginated(
            {"next_cursor": "abc"},
            [{"x": 1}, {"x": 2}],
            item_key="users",
            extra={"sort": "Latest"},
        )
        assert out == {
            "count": 2,
            "users": [{"x": 1}, {"x": 2}],
            "next_cursor": "abc",
            "sort": "Latest",
        }
