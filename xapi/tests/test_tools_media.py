"""Tests for media upload tool."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from xapi_mcp.tools import media as tools


@pytest.mark.asyncio
@pytest.mark.unit
class TestUploadMedia:
    async def test_rejects_missing_file(self, fake_client):
        out = await tools.x_upload_media("/no/such/file.png")
        assert "local file not found" in out["error"]
        fake_client.v1.media_upload.assert_not_called()

    async def test_uploads(self, fake_client, tmp_path):
        f = tmp_path / "img.png"
        f.write_bytes(b"\x89PNG")
        fake_client.v1.media_upload.return_value = SimpleNamespace(
            media_id_string="MID123", media_id=123, size=4, type="photo"
        )
        out = await tools.x_upload_media(str(f))
        assert out["media_id"] == "MID123"
        assert out["size"] == 4
