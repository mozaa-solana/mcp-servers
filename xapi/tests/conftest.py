"""Test fixtures — fully offline. Patches XClient at the registry boundary
so no real OAuth credentials or network calls are needed."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from xapi_mcp.budget import DailyBudget
from xapi_mcp.config import Config


def _make_config(**overrides) -> Config:
    base = dict(
        api_key="ak",
        api_secret="as",
        access_token="at",
        access_token_secret="ats",
        handle="@test",
        budget_usd_per_day=None,
        dry_run=False,
    )
    base.update(overrides)
    return Config(**base)


@pytest.fixture
def fake_client() -> MagicMock:
    """A MagicMock that mimics XClient with .v2 (tweepy.Client) + .v1 (tweepy.API)."""
    client = MagicMock()
    client.v2 = MagicMock()
    client.v1 = MagicMock()
    return client


@pytest.fixture(autouse=True)
def _patch_registry(monkeypatch, fake_client):
    """Replace get_config / get_client / get_budget singletons.

    Auto-applied to every test — keeps the entire suite offline."""
    from xapi_mcp.tools import _registry as reg

    cfg = _make_config()
    fake_client.cfg = cfg
    budget = DailyBudget(cap_usd=None)

    # lru_cache wrappers: clear and replace the underlying function.
    reg.get_config.cache_clear()
    reg.get_client.cache_clear()
    reg.get_budget.cache_clear()

    monkeypatch.setattr(reg, "get_config", lambda: cfg)
    monkeypatch.setattr(reg, "get_client", lambda: fake_client)
    monkeypatch.setattr(reg, "get_budget", lambda: budget)

    # The tool modules captured the originals at import-time — patch
    # there too so decorators that call get_config()/get_budget()/get_client()
    # see the test versions.
    for mod_name in (
        "me", "posts", "users", "dms", "media", "budget",
        "account", "bookmarks", "research", "analytics",
    ):
        mod = __import__(f"xapi_mcp.tools.{mod_name}", fromlist=["x"])
        if hasattr(mod, "get_config"):
            monkeypatch.setattr(mod, "get_config", lambda c=cfg: c)
        if hasattr(mod, "get_client"):
            monkeypatch.setattr(mod, "get_client", lambda c=fake_client: c)
        if hasattr(mod, "get_budget"):
            monkeypatch.setattr(mod, "get_budget", lambda b=budget: b)

    return SimpleNamespace(cfg=cfg, client=fake_client, budget=budget)


@pytest.fixture
def patched(monkeypatch, fake_client):
    """Convenience: same as the autouse fixture but returns the bag for
    tests that want to override (e.g. set dry_run=True)."""
    from xapi_mcp.tools import _registry as reg
    return SimpleNamespace(
        cfg=reg.get_config(),
        client=fake_client,
        budget=reg.get_budget(),
    )


def set_dry_run(monkeypatch, value: bool = True) -> Config:
    """Helper to flip dry_run on the registry for one test."""
    from xapi_mcp.tools import _registry as reg

    cfg = _make_config(dry_run=value)
    monkeypatch.setattr(reg, "get_config", lambda: cfg)
    for mod_name in ("posts", "users", "dms", "account", "bookmarks"):
        mod = __import__(f"xapi_mcp.tools.{mod_name}", fromlist=["x"])
        if hasattr(mod, "get_config"):
            monkeypatch.setattr(mod, "get_config", lambda c=cfg: c)
    return cfg


def set_budget(monkeypatch, cap_usd: float | None) -> DailyBudget:
    from xapi_mcp.budget import DailyBudget
    from xapi_mcp.tools import _registry as reg

    budget = DailyBudget(cap_usd=cap_usd)
    monkeypatch.setattr(reg, "get_budget", lambda: budget)
    for mod_name in (
        "me", "posts", "users", "dms", "budget",
        "account", "bookmarks", "research", "analytics",
    ):
        mod = __import__(f"xapi_mcp.tools.{mod_name}", fromlist=["x"])
        if hasattr(mod, "get_budget"):
            monkeypatch.setattr(mod, "get_budget", lambda b=budget: b)
    return budget


def program_v2_response(method_name: str, client, data) -> None:
    """Make ``client.v2.<method_name>(...)`` return a Response-like object
    whose ``.data`` is ``data`` and ``.meta`` is empty."""
    resp = SimpleNamespace(data=data, meta={}, includes={}, errors=[])
    getattr(client.v2, method_name).return_value = resp
