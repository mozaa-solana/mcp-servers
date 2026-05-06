"""Tests for revisions and permissions tool layers."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gdrive_mcp.normalize import GOOGLE_DOC
from gdrive_mcp.tools import permissions as perm_tools
from gdrive_mcp.tools import revisions as rev_tools
from tests.conftest import (
    program_files_get,
    program_permissions_list,
    program_revisions_list,
)


def _program_revision_media(svc: MagicMock, payload: bytes) -> None:
    svc.revisions.return_value.get_media.return_value.execute.return_value = payload


@pytest.mark.asyncio
@pytest.mark.unit
class TestListRevisions:
    async def test_returns_trimmed(self, svc):
        program_revisions_list(
            svc,
            {
                "revisions": [
                    {"id": "r1", "modifiedTime": "2026-05-01T00:00:00Z", "size": "10"}
                ]
            },
        )
        out = await rev_tools.drive_list_revisions("F")
        assert out["count"] == 1
        assert out["revisions"][0]["size"] == 10
        assert out["file_id"] == "F"


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetRevision:
    async def test_text_revision_returns_content(self, svc):
        program_files_get(svc, {"name": "x.md", "mimeType": "text/markdown"})
        _program_revision_media(svc, b"hello")
        out = await rev_tools.drive_get_revision("F", "r1")
        assert out["content"] == "hello"
        assert out["revision_id"] == "r1"

    async def test_native_revision_returns_error(self, svc):
        program_files_get(svc, {"name": "doc", "mimeType": GOOGLE_DOC})
        out = await rev_tools.drive_get_revision("F", "r1")
        assert "historical revisions of" in out["error"]

    async def test_binary_revision_rejected(self, svc):
        program_files_get(svc, {"name": "p", "mimeType": "image/png"})
        out = await rev_tools.drive_get_revision("F", "r1")
        assert "binary" in out["error"]


@pytest.mark.asyncio
@pytest.mark.unit
class TestPermissions:
    async def test_lists_permissions(self, svc):
        program_permissions_list(
            svc,
            {
                "permissions": [
                    {"id": "p1", "type": "user", "role": "writer", "emailAddress": "u@x"}
                ]
            },
        )
        out = await perm_tools.drive_list_permissions("F")
        assert out["count"] == 1
        assert out["permissions"][0]["role"] == "writer"
        assert out["file_id"] == "F"
