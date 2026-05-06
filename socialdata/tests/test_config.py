"""Tests for env-driven Config loader."""
from __future__ import annotations

import pytest

from socialdata_mcp.config import Config, ConfigError


@pytest.mark.unit
class TestConfigFromEnv:
    def test_loads_required_key(self):
        cfg = Config.from_env({"SOCIALDATA_API_KEY": "abc"})
        assert cfg.api_key == "abc"
        assert cfg.base_url == "https://api.socialdata.tools"
        assert cfg.timeout_seconds == 30.0

    def test_strips_trailing_slash_from_base_url(self):
        cfg = Config.from_env(
            {"SOCIALDATA_API_KEY": "k", "SOCIALDATA_BASE_URL": "https://example.test/"}
        )
        assert cfg.base_url == "https://example.test"

    def test_custom_timeout(self):
        cfg = Config.from_env(
            {"SOCIALDATA_API_KEY": "k", "SOCIALDATA_TIMEOUT": "5"}
        )
        assert cfg.timeout_seconds == 5.0

    def test_missing_key_raises(self):
        with pytest.raises(ConfigError):
            Config.from_env({})

    def test_blank_key_raises(self):
        with pytest.raises(ConfigError):
            Config.from_env({"SOCIALDATA_API_KEY": "   "})

    def test_invalid_timeout_raises(self):
        with pytest.raises(ConfigError):
            Config.from_env({"SOCIALDATA_API_KEY": "k", "SOCIALDATA_TIMEOUT": "abc"})
