"""Tool registration smoke test — ensure all 18 @mcp.tool() decorators ran."""
from __future__ import annotations

import pytest

import gdrive_mcp.tools  # noqa: F401  — triggers registration
from gdrive_mcp.tools._registry import mcp


EXPECTED = {
    # about
    "drive_about",
    "drive_list_shared_with_me",
    # files (read)
    "drive_list_files",
    "drive_search",
    "drive_get_metadata",
    "drive_get_folder_tree",
    # files (write)
    "drive_create_folder",
    "drive_rename_file",
    "drive_move_file",
    "drive_trash_file",
    # content
    "drive_get_content",
    "drive_export_file",
    "drive_upload_file",
    "drive_create_text_file",
    "drive_update_file_content",
    # revisions
    "drive_list_revisions",
    "drive_get_revision",
    # permissions
    "drive_list_permissions",
}


@pytest.mark.asyncio
async def test_all_tools_registered():
    listed = await mcp.list_tools()
    names = {t.name for t in listed}
    missing = EXPECTED - names
    extra = names - EXPECTED
    assert not missing, f"missing: {sorted(missing)}"
    assert not extra, f"unexpected extra: {sorted(extra)}"
    assert len(EXPECTED) == 18
