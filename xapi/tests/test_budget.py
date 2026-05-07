"""Tests for the in-memory daily budget guard."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from xapi_mcp.budget import BudgetExceeded, DailyBudget


@pytest.mark.unit
class TestDailyBudget:
    def test_no_cap_is_unlimited(self):
        b = DailyBudget(cap_usd=None)
        b.check(999_999.0)  # no raise
        b.record(999_999.0)
        snap = b.snapshot()
        assert snap["cap_usd"] is None
        assert snap["remaining_usd"] is None

    def test_check_blocks_when_would_exceed(self):
        b = DailyBudget(cap_usd=1.0)
        b.record(0.95)
        with pytest.raises(BudgetExceeded):
            b.check(0.10)

    def test_check_allows_at_cap(self):
        b = DailyBudget(cap_usd=1.0)
        b.record(0.5)
        b.check(0.5)  # exactly at cap, no raise

    def test_record_accumulates(self):
        b = DailyBudget(cap_usd=10.0)
        b.record(0.1)
        b.record(0.2)
        snap = b.snapshot()
        assert snap["spent_usd"] == 0.3

    def test_resets_on_new_utc_day(self):
        b = DailyBudget(cap_usd=1.0)
        b.record(0.99)

        # Force the date to roll forward.
        with patch("xapi_mcp.budget.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2099, 1, 1, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            snap = b.snapshot()
            assert snap["spent_usd"] == 0.0
            b.check(0.99)  # would have failed yesterday — passes today

    def test_snapshot_remaining_correct(self):
        b = DailyBudget(cap_usd=2.0)
        b.record(0.5)
        snap = b.snapshot()
        assert snap["remaining_usd"] == 1.5
