"""Tests for the diagnostic x_budget_status tool."""
from __future__ import annotations

import pytest

from xapi_mcp.tools import budget as tools
from tests.conftest import set_budget


@pytest.mark.asyncio
@pytest.mark.unit
class TestBudgetStatus:
    async def test_unset_cap(self):
        out = await tools.x_budget_status()
        assert out["cap_usd"] is None
        assert out["spent_usd"] == 0.0

    async def test_with_cap(self, monkeypatch):
        b = set_budget(monkeypatch, 5.0)
        b.record(1.5)
        out = await tools.x_budget_status()
        assert out["cap_usd"] == 5.0
        assert out["spent_usd"] == 1.5
        assert out["remaining_usd"] == 3.5
