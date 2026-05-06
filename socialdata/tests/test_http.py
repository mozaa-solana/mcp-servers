"""Tests for the low-level HTTP wrapper."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from socialdata_mcp import http as http_mod
from socialdata_mcp.config import Config
from socialdata_mcp.http import SocialDataAPIError, request_json


CFG = Config(api_key="k", base_url="https://api.example.test", timeout_seconds=10.0)


def _stub_client(*, status: int = 200, payload=None) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.json = MagicMock(return_value=payload or {})
    resp.text = "raw-body"

    client = MagicMock()
    client.request = AsyncMock(return_value=resp)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.mark.asyncio
@pytest.mark.unit
class TestRequestJson:
    async def test_get_builds_url_from_relative_path(self, monkeypatch):
        client = _stub_client(payload={"ok": True})
        monkeypatch.setattr(http_mod, "make_async_client", lambda cfg: client)

        out = await request_json(CFG, "GET", "/twitter/search", params={"q": 1})

        assert out == {"ok": True}
        client.request.assert_awaited_once_with(
            "GET", "https://api.example.test/twitter/search", params={"q": 1}, json=None
        )

    async def test_post_passes_json_body(self, monkeypatch):
        client = _stub_client(payload={"ok": True})
        monkeypatch.setattr(http_mod, "make_async_client", lambda cfg: client)

        await request_json(CFG, "POST", "/x", json={"ids": [1, 2]})

        client.request.assert_awaited_once_with(
            "POST", "https://api.example.test/x", params=None, json={"ids": [1, 2]}
        )

    async def test_4xx_raises_with_parsed_body(self, monkeypatch):
        client = _stub_client(status=404, payload={"error": "not found"})
        monkeypatch.setattr(http_mod, "make_async_client", lambda cfg: client)

        with pytest.raises(SocialDataAPIError) as ei:
            await request_json(CFG, "GET", "/missing")
        assert ei.value.status_code == 404
        assert ei.value.body == {"error": "not found"}

    async def test_4xx_with_non_json_body_falls_back_to_text(self, monkeypatch):
        client = _stub_client(status=500)
        client.request.return_value.json.side_effect = ValueError("not json")
        monkeypatch.setattr(http_mod, "make_async_client", lambda cfg: client)

        with pytest.raises(SocialDataAPIError) as ei:
            await request_json(CFG, "GET", "/boom")
        assert ei.value.status_code == 500
        assert ei.value.body == "raw-body"

    async def test_absolute_url_passes_through(self, monkeypatch):
        client = _stub_client(payload={"ok": True})
        monkeypatch.setattr(http_mod, "make_async_client", lambda cfg: client)

        await request_json(CFG, "GET", "https://other.test/abs")

        client.request.assert_awaited_once_with(
            "GET", "https://other.test/abs", params=None, json=None
        )
