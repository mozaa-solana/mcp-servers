"""Tests for tools/about.py."""
from __future__ import annotations

import pytest

from gdrive_mcp.tools import about as tools
from tests.conftest import (
    program_about_get,
    program_drives_list,
    program_files_list,
)


@pytest.mark.asyncio
@pytest.mark.unit
class TestAbout:
    async def test_returns_identity_and_quota(self, svc):
        program_about_get(
            svc,
            {
                "user": {"emailAddress": "bot@x.iam", "displayName": "Bot"},
                "storageQuota": {"limit": "100", "usage": "10", "usageInDrive": "5"},
            },
        )

        out = await tools.drive_about()

        assert out["service_account_email"] == "bot@x.iam"
        assert out["quota"] == {"limit": 100, "usage": 10, "usage_in_drive": 5}

    async def test_handles_missing_quota(self, svc):
        program_about_get(svc, {"user": {"emailAddress": "bot@x"}, "storageQuota": {}})

        out = await tools.drive_about()

        assert out["quota"] == {"limit": None, "usage": None, "usage_in_drive": None}


@pytest.mark.asyncio
@pytest.mark.unit
class TestSharedWithMe:
    async def test_returns_trimmed_list(self, svc):
        program_files_list(
            svc,
            {
                "files": [
                    {"id": "f1", "name": "A", "mimeType": "text/plain", "parents": ["P"]}
                ],
                "nextPageToken": "next",
            },
        )

        out = await tools.drive_list_shared_with_me(max_results=20)

        assert out["count"] == 1
        assert out["files"][0]["name"] == "A"
        assert out["next_cursor"] == "next"

    async def test_clamps_max_results(self, svc):
        program_files_list(svc, {"files": []})
        await tools.drive_list_shared_with_me(max_results=99999)
        kwargs = svc.files.return_value.list.call_args.kwargs
        assert kwargs["pageSize"] == 1000


@pytest.mark.asyncio
@pytest.mark.unit
class TestListDrives:
    async def test_returns_trimmed(self, svc):
        program_drives_list(
            svc,
            {
                "drives": [
                    {"id": "D1", "name": "My Shared", "createdTime": "2026-01-01"},
                    {"id": "D2", "name": "Other", "hidden": True},
                ],
                "nextPageToken": "next",
            },
        )
        out = await tools.drive_list_drives(max_results=10)
        assert out["count"] == 2
        assert out["drives"][0] == {
            "id": "D1", "name": "My Shared",
            "created": "2026-01-01", "hidden": False,
        }
        assert out["drives"][1]["hidden"] is True
        assert out["next_cursor"] == "next"

    async def test_empty_list_normal_on_personal_gmail(self, svc):
        program_drives_list(svc, {"drives": []})
        out = await tools.drive_list_drives()
        assert out["count"] == 0
