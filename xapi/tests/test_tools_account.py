"""Tests for profile-management tools (v1.1 endpoints)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from xapi_mcp.tools import account as tools
from tests.conftest import set_dry_run


@pytest.mark.asyncio
@pytest.mark.unit
class TestUpdateProfile:
    async def test_rejects_when_no_fields(self, fake_client):
        out = await tools.x_update_profile()
        assert "at least one field" in out["error"]
        fake_client.v1.update_profile.assert_not_called()

    async def test_passes_only_provided_fields(self, fake_client):
        fake_client.v1.update_profile.return_value = SimpleNamespace(
            _json={"name": "New Name", "description": "bio"}
        )
        out = await tools.x_update_profile(name="New Name", description="bio")
        assert out["updated"] is True
        kwargs = fake_client.v1.update_profile.call_args.kwargs
        assert kwargs == {"name": "New Name", "description": "bio"}

    async def test_dry_run(self, monkeypatch, fake_client):
        set_dry_run(monkeypatch, True)
        out = await tools.x_update_profile(name="x")
        assert out["dry_run"] is True
        fake_client.v1.update_profile.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
class TestUpdateProfileImage:
    async def test_rejects_missing_file(self, fake_client):
        out = await tools.x_update_profile_image("/no/such.png")
        assert "local file not found" in out["error"]

    async def test_uploads(self, fake_client, tmp_path):
        f = tmp_path / "avatar.png"
        f.write_bytes(b"\x89PNG")
        fake_client.v1.update_profile_image.return_value = SimpleNamespace(
            _json={"name": "x"}
        )
        out = await tools.x_update_profile_image(str(f))
        assert out["updated"] is True
