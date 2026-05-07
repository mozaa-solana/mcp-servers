"""In-memory daily USD spend tracker.

Resets at UTC midnight. Persists nothing — restarting the MCP server
zeroes the counter. That's intentional for v1 (process-per-user model
keeps state simple). If you need durable accounting, layer a SQLite
store on top.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


class BudgetExceeded(RuntimeError):
    """Raised when a tool call would push spend above the daily cap."""


@dataclass
class DailyBudget:
    cap_usd: float | None
    _date: str = ""
    _spent: float = 0.0

    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _roll_if_new_day(self) -> None:
        d = self._today()
        if d != self._date:
            self._date = d
            self._spent = 0.0

    def check(self, cost_usd: float) -> None:
        """Raise BudgetExceeded if recording ``cost_usd`` would exceed cap.

        No-op when cap is None (unlimited)."""
        if self.cap_usd is None:
            return
        self._roll_if_new_day()
        if self._spent + cost_usd > self.cap_usd:
            raise BudgetExceeded(
                f"Daily budget ${self.cap_usd:.2f} would be exceeded "
                f"(already spent ${self._spent:.4f}, this call ${cost_usd:.4f}). "
                "Raise X_BUDGET_USD_PER_DAY or wait for UTC midnight."
            )

    def record(self, cost_usd: float) -> None:
        """Record actual spend after a successful API call."""
        self._roll_if_new_day()
        self._spent += cost_usd

    def snapshot(self) -> dict[str, float | str | None]:
        self._roll_if_new_day()
        return {
            "date_utc": self._date,
            "cap_usd": self.cap_usd,
            "spent_usd": round(self._spent, 4),
            "remaining_usd": (
                round(self.cap_usd - self._spent, 4) if self.cap_usd is not None else None
            ),
        }
