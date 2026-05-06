from __future__ import annotations

import pytest

from socialdata_mcp.tools import search as tools


SAMPLE_TWEET = {
    "id_str": "1",
    "user": {"screen_name": "alice"},
    "full_text": "hi",
}


@pytest.mark.asyncio
@pytest.mark.unit
class TestTwitterSearch:
    async def test_returns_trimmed_tweets(self, stub_request):
        stub_request.set({"tweets": [SAMPLE_TWEET, SAMPLE_TWEET], "next_cursor": "n"})

        result = await tools.twitter_search("AI", max_results=10)

        assert result["count"] == 2
        assert result["query"] == "AI"
        assert result["sort"] == "Latest"
        assert result["next_cursor"] == "n"
        assert result["tweets"][0]["author"]["screen_name"] == "alice"

    async def test_clamps_max_results_to_50(self, stub_request):
        stub_request.set({"tweets": [SAMPLE_TWEET] * 100})
        result = await tools.twitter_search("AI", max_results=999)
        assert result["count"] == 50

    async def test_clamps_max_results_to_1(self, stub_request):
        stub_request.set({"tweets": [SAMPLE_TWEET]})
        result = await tools.twitter_search("AI", max_results=0)
        assert result["count"] == 1

    async def test_normalizes_sort_to_top(self, stub_request):
        stub_request.set({"tweets": []})
        await tools.twitter_search("AI", sort="top")
        assert stub_request.last["params"]["type"] == "Top"

    async def test_normalizes_unknown_sort_to_latest(self, stub_request):
        stub_request.set({"tweets": []})
        await tools.twitter_search("AI", sort="banana")
        assert stub_request.last["params"]["type"] == "Latest"

    async def test_passes_cursor_through(self, stub_request):
        stub_request.set({"tweets": []})
        await tools.twitter_search("AI", cursor="C1")
        assert stub_request.last["params"]["cursor"] == "C1"

    async def test_data_key_fallback(self, stub_request):
        stub_request.set({"data": [SAMPLE_TWEET]})
        result = await tools.twitter_search("AI")
        assert result["count"] == 1
