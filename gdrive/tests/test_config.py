"""Tests for env-driven Config loader."""
from __future__ import annotations

import pytest

from gdrive_mcp.config import Config, ConfigError


@pytest.mark.unit
class TestConfig:
    def test_loads_required_path(self, tmp_path):
        key = tmp_path / "sa.json"
        key.write_text("{}")
        cfg = Config.from_env({"GOOGLE_APPLICATION_CREDENTIALS": str(key)})
        assert cfg.credentials_path == str(key)
        assert cfg.working_folder_id is None
        assert cfg.default_page_size == 100

    def test_falls_back_to_project_var(self, tmp_path):
        key = tmp_path / "sa.json"
        key.write_text("{}")
        cfg = Config.from_env({"GDRIVE_SERVICE_ACCOUNT_JSON": str(key)})
        assert cfg.credentials_path == str(key)

    def test_missing_path_raises(self):
        with pytest.raises(ConfigError):
            Config.from_env({})

    def test_nonexistent_path_raises(self):
        with pytest.raises(ConfigError):
            Config.from_env({"GOOGLE_APPLICATION_CREDENTIALS": "/no/such/file"})

    def test_working_folder_id_loaded(self, tmp_path):
        key = tmp_path / "sa.json"
        key.write_text("{}")
        cfg = Config.from_env(
            {
                "GOOGLE_APPLICATION_CREDENTIALS": str(key),
                "GDRIVE_WORKING_FOLDER_ID": "abc",
            }
        )
        assert cfg.working_folder_id == "abc"

    def test_blank_working_folder_treated_as_none(self, tmp_path):
        key = tmp_path / "sa.json"
        key.write_text("{}")
        cfg = Config.from_env(
            {
                "GOOGLE_APPLICATION_CREDENTIALS": str(key),
                "GDRIVE_WORKING_FOLDER_ID": "   ",
            }
        )
        assert cfg.working_folder_id is None

    def test_invalid_page_size_raises(self, tmp_path):
        key = tmp_path / "sa.json"
        key.write_text("{}")
        with pytest.raises(ConfigError):
            Config.from_env(
                {
                    "GOOGLE_APPLICATION_CREDENTIALS": str(key),
                    "GDRIVE_DEFAULT_PAGE_SIZE": "abc",
                }
            )
