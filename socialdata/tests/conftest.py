"""Shared pytest fixtures for socialdata-mcp tests.

Tests run against a stub HTTP layer — :func:`socialdata_mcp.http.request_json`
is monkeypatched to return scripted responses. This way tests cover the full
api/* and tools/* code paths without depending on env variables or network.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure the package is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Tools resolve config lazily, but server.py imports get_config eagerly only at
# main(). Setting a placeholder lets get_config() succeed if any test happens to
# trigger it.
os.environ.setdefault("SOCIALDATA_API_KEY", "test-key-for-pytest")


@pytest.fixture
def stub_request(monkeypatch):
    """Patch :func:`socialdata_mcp.http.request_json` with a scripted stub.

    Yields a controller exposing:
      • ``set(payload)`` / ``set_response(payload)`` — fixed response for next call
      • ``script([p1, p2, ...])`` — sequence of responses (one per call)
      • ``calls`` — list of recorded ``(method, path, params, json)`` tuples
    """
    from socialdata_mcp import http as http_mod
    from socialdata_mcp.api import (
        communities,
        lists,
        search,
        social_actions,
        spaces,
        tweets,
        users,
    )

    state: dict[str, Any] = {"queue": [], "default": {}, "calls": []}

    async def fake_request(config, method, path, *, params=None, json=None):
        state["calls"].append(
            {"method": method, "path": path, "params": params, "json": json}
        )
        if state["queue"]:
            return state["queue"].pop(0)
        return state["default"]

    # Patch the symbol in every api submodule that imported it `from ..http`.
    monkeypatch.setattr(http_mod, "request_json", fake_request)
    for mod in (search, users, tweets, lists, communities, spaces, social_actions):
        monkeypatch.setattr(mod, "request_json", fake_request)

    class Controller:
        def set(self, payload: Any) -> None:
            state["default"] = payload

        set_response = set

        def script(self, payloads: list[Any]) -> None:
            state["queue"] = list(payloads)

        @property
        def calls(self) -> list[dict[str, Any]]:
            return state["calls"]

        @property
        def last(self) -> dict[str, Any] | None:
            return state["calls"][-1] if state["calls"] else None

    return Controller()
