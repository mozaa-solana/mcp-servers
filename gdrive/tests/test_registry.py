"""Tool registration smoke test — ensure all @mcp.tool() decorators ran."""
from __future__ import annotations

import pytest

import gdrive_mcp.tools  # noqa: F401  — triggers registration
from gdrive_mcp.tools._registry import mcp


EXPECTED = {
    # ---- Drive (21) ----
    # discovery
    "drive_about",
    "drive_list_shared_with_me",
    "drive_list_drives",
    # files (read)
    "drive_list_files",
    "drive_search",
    "drive_get_metadata",
    "drive_get_folder_tree",
    # files (write)
    "drive_create_folder",
    "drive_copy_file",
    "drive_rename_file",
    "drive_move_file",
    "drive_trash_file",
    "drive_untrash_file",
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
    # ---- Sheets (21) ----
    # read
    "sheets_get_metadata",
    "sheets_get_values",
    "sheets_batch_get_values",
    # write values
    "sheets_update_values",
    "sheets_append_values",
    "sheets_clear_values",
    "sheets_batch_update_values",
    "sheets_find_replace",
    # structure (tab CRUD)
    "sheets_create_spreadsheet",
    "sheets_add_sheet",
    "sheets_delete_sheet",
    "sheets_rename_sheet",
    "sheets_duplicate_sheet",
    "sheets_copy_sheet_to_spreadsheet",
    # structure (rows/cols)
    "sheets_insert_rows",
    "sheets_delete_rows",
    "sheets_insert_cols",
    "sheets_delete_cols",
    "sheets_sort_range",
    # layout
    "sheets_freeze",
    "sheets_merge_cells",
    # ---- Docs (20) ----
    # read
    "docs_get",
    "docs_get_text",
    # create
    "docs_create",
    # text editing
    "docs_insert_text",
    "docs_delete_range",
    "docs_replace_text",
    # styling
    "docs_update_text_style",
    "docs_update_paragraph_style",
    # lists
    "docs_create_bullets",
    "docs_delete_bullets",
    # tables
    "docs_insert_table",
    "docs_insert_table_row",
    "docs_delete_table_row",
    "docs_insert_table_column",
    "docs_delete_table_column",
    # images
    "docs_insert_image",
    "docs_replace_image",
    # headers/footers/footnotes
    "docs_create_header",
    "docs_create_footer",
    "docs_create_footnote",
}


@pytest.mark.asyncio
async def test_all_tools_registered():
    listed = await mcp.list_tools()
    names = {t.name for t in listed}
    missing = EXPECTED - names
    extra = names - EXPECTED
    assert not missing, f"missing: {sorted(missing)}"
    assert not extra, f"unexpected extra: {sorted(extra)}"
    assert len(EXPECTED) == 62
