"""Tool registration smoke test — ensure all 18 @mcp.tool() decorators ran."""
from __future__ import annotations

import pytest

import gdrive_mcp.tools  # noqa: F401  — triggers registration
from gdrive_mcp.tools._registry import mcp


EXPECTED = {
    # ---- Drive (18) ----
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
    # ---- Sheets (12) ----
    # read
    "sheets_get_metadata",
    "sheets_get_values",
    "sheets_batch_get_values",
    # write values
    "sheets_update_values",
    "sheets_append_values",
    "sheets_clear_values",
    "sheets_batch_update_values",
    # structure
    "sheets_create_spreadsheet",
    "sheets_add_sheet",
    "sheets_delete_sheet",
    "sheets_rename_sheet",
    "sheets_duplicate_sheet",
}


@pytest.mark.asyncio
async def test_all_tools_registered():
    listed = await mcp.list_tools()
    names = {t.name for t in listed}
    missing = EXPECTED - names
    extra = names - EXPECTED
    assert not missing, f"missing: {sorted(missing)}"
    assert not extra, f"unexpected extra: {sorted(extra)}"
    assert len(EXPECTED) == 30
