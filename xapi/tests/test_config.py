"""Tests for env-driven Config loader."""
from __future__ import annotations

import pytest

from xapi_mcp.config import Config, ConfigError


@pytest.mark.unit
class TestConfig:
    BASE = {
        "X_API_KEY": "ak",
        "X_API_SECRET": "as",
        "X_ACCESS_TOKEN": "at",
        "X_ACCESS_TOKEN_SECRET": "ats",
    }

    def test_loads_required(self):
        cfg = Config.from_env(self.BASE)
        assert cfg.api_key == "ak"
        assert cfg.access_token_secret == "ats"
        assert cfg.budget_usd_per_day is None
        assert cfg.dry_run is False
        assert cfg.handle is None

    def test_handle_loaded(self):
        cfg = Config.from_env({**self.BASE, "X_HANDLE": "@alice"})
        assert cfg.handle == "@alice"

    def test_handle_blank_treated_as_none(self):
        cfg = Config.from_env({**self.BASE, "X_HANDLE": "   "})
        assert cfg.handle is None

    def test_missing_required_raises(self):
        partial = dict(self.BASE)
        del partial["X_ACCESS_TOKEN"]
        with pytest.raises(ConfigError):
            Config.from_env(partial)

    def test_blank_required_raises(self):
        with pytest.raises(ConfigError):
            Config.from_env({**self.BASE, "X_API_KEY": "   "})

    def test_budget_loaded(self):
        cfg = Config.from_env({**self.BASE, "X_BUDGET_USD_PER_DAY": "5.0"})
        assert cfg.budget_usd_per_day == 5.0

    def test_budget_invalid_raises(self):
        with pytest.raises(ConfigError):
            Config.from_env({**self.BASE, "X_BUDGET_USD_PER_DAY": "abc"})

    def test_budget_negative_raises(self):
        with pytest.raises(ConfigError):
            Config.from_env({**self.BASE, "X_BUDGET_USD_PER_DAY": "-1"})

    def test_dry_run_truthy(self):
        for v in ("1", "true", "yes", "TRUE", "Yes"):
            cfg = Config.from_env({**self.BASE, "X_DRY_RUN": v})
            assert cfg.dry_run is True, v

    def test_dry_run_falsy(self):
        for v in ("0", "false", "", "no", "off"):
            cfg = Config.from_env({**self.BASE, "X_DRY_RUN": v})
            assert cfg.dry_run is False, v

    def test_frozen(self):
        cfg = Config.from_env(self.BASE)
        with pytest.raises(Exception):
            cfg.api_key = "x"  # type: ignore[misc]
