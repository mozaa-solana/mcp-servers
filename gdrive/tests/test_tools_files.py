"""Tests for tools/files.py — list / search / metadata / tree / write metadata mutations."""
from __future__ import annotations

import pytest

from gdrive_mcp.normalize import GOOGLE_FOLDER
from gdrive_mcp.safety import SafetyViolation
from gdrive_mcp.tools import files as tools
from tests.conftest import (
    program_files_copy,
    program_files_create,
    program_files_get,
    program_files_list,
    program_files_update,
)


# --------------------------------------------------------------------------
# Read
# --------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
class TestListFiles:
    async def test_basic_query_built(self, svc):
        program_files_list(svc, {"files": []})
        await tools.drive_list_files(folder_id="F", name_contains="budget")
        q = svc.files.return_value.list.call_args.kwargs["q"]
        assert "'F' in parents" in q
        assert "name contains 'budget'" in q
        assert "trashed = false" in q

    async def test_no_filters_just_trashed(self, svc):
        program_files_list(svc, {"files": []})
        await tools.drive_list_files()
        q = svc.files.return_value.list.call_args.kwargs["q"]
        assert q == "trashed = false"

    async def test_escapes_apostrophe_in_name(self, svc):
        program_files_list(svc, {"files": []})
        await tools.drive_list_files(name_contains="O'Reilly")
        q = svc.files.return_value.list.call_args.kwargs["q"]
        assert r"O\'Reilly" in q


@pytest.mark.asyncio
@pytest.mark.unit
class TestSearch:
    async def test_appends_trashed_clause(self, svc):
        program_files_list(svc, {"files": []})
        await tools.drive_search("name contains 'roadmap'")
        q = svc.files.return_value.list.call_args.kwargs["q"]
        assert q == "(name contains 'roadmap') and trashed = false"

    async def test_returns_query_in_envelope(self, svc):
        program_files_list(
            svc, {"files": [{"id": "1", "name": "X", "mimeType": "text/plain"}]}
        )
        out = await tools.drive_search("foo")
        assert out["query"] == "foo"
        assert out["count"] == 1


@pytest.mark.asyncio
@pytest.mark.unit
class TestMetadata:
    async def test_get_metadata(self, svc):
        program_files_get(
            svc, {"id": "F", "name": "doc", "mimeType": "text/plain"}
        )
        out = await tools.drive_get_metadata("F")
        assert out["name"] == "doc"


@pytest.mark.asyncio
@pytest.mark.unit
class TestFolderTree:
    async def test_walks_folders(self, svc):
        # Root has 1 folder + 1 file; nested folder is empty.
        responses = [
            {
                "files": [
                    {"id": "sub", "name": "Sub", "mimeType": GOOGLE_FOLDER},
                    {"id": "leaf", "name": "Leaf", "mimeType": "text/plain"},
                ]
            },
            {"files": []},
        ]
        svc.files.return_value.list.return_value.execute.side_effect = responses

        out = await tools.drive_get_folder_tree("ROOT", max_depth=2)

        assert out["count"] == 2
        names = [e["name"] for e in out["entries"]]
        assert names == ["Sub", "Leaf"]
        assert out["max_depth"] == 2

    async def test_respects_max_depth_zero(self, svc):
        program_files_list(svc, {"files": []})
        out = await tools.drive_get_folder_tree("ROOT", max_depth=0)
        assert out["count"] == 0
        # No API call expected since depth=0 short-circuits the BFS.
        assert svc.files.return_value.list.call_count == 0


# --------------------------------------------------------------------------
# Write — safety rail interactions
# --------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
class TestCreateFolder:
    async def test_no_safety_passes_through(self, svc):
        program_files_create(svc, {"id": "NEW", "name": "N", "mimeType": GOOGLE_FOLDER})
        out = await tools.drive_create_folder("N")
        assert out["id"] == "NEW"

    async def test_safety_rail_blocks_outside_parent(self, svc_with_safety):
        svc, _ = svc_with_safety
        # parent walk returns no parents → outside rail
        program_files_get(svc, {"parents": []})
        with pytest.raises(SafetyViolation):
            await tools.drive_create_folder("N", parent_id="OUTSIDE")

    async def test_safety_rail_allows_inside_parent(self, svc_with_safety):
        svc, root = svc_with_safety
        program_files_get(svc, {"parents": [root]})
        program_files_create(svc, {"id": "NEW", "name": "N", "mimeType": GOOGLE_FOLDER})
        out = await tools.drive_create_folder("N", parent_id="INSIDE")
        assert out["id"] == "NEW"


@pytest.mark.asyncio
@pytest.mark.unit
class TestRenameMoveTrash:
    async def test_rename_blocked_outside_rail(self, svc_with_safety):
        svc, _ = svc_with_safety
        program_files_get(svc, {"parents": []})
        with pytest.raises(SafetyViolation):
            await tools.drive_rename_file("F", "new")

    async def test_move_validates_both_endpoints(self, svc_with_safety):
        svc, root = svc_with_safety
        # First lookup (file_id), second lookup (new_parent_id)
        svc.files.return_value.get.return_value.execute.side_effect = [
            {"parents": [root]},  # file inside
            {"parents": []},  # new_parent outside
        ]
        with pytest.raises(SafetyViolation):
            await tools.drive_move_file("F", "NEW_PARENT")

    async def test_trash_returns_trimmed(self, svc):
        program_files_update(svc, {"id": "F", "name": "g", "trashed": True})
        out = await tools.drive_trash_file("F")
        assert out["trashed"] is True


@pytest.mark.asyncio
@pytest.mark.unit
class TestUntrash:
    async def test_returns_restored_file(self, svc):
        program_files_update(svc, {"id": "F", "name": "g", "trashed": False})
        out = await tools.drive_untrash_file("F")
        assert out["trashed"] is False

    async def test_safety_rail_blocks(self, svc_with_safety):
        svc, _ = svc_with_safety
        program_files_get(svc, {"parents": []})
        with pytest.raises(SafetyViolation):
            await tools.drive_untrash_file("F")


@pytest.mark.asyncio
@pytest.mark.unit
class TestCopyFile:
    async def test_copy_with_new_name_and_parent(self, svc):
        program_files_copy(
            svc, {"id": "NEW", "name": "copy.md", "mimeType": "text/markdown"}
        )
        out = await tools.drive_copy_file("F", new_name="copy.md", parent_id="P")
        assert out["id"] == "NEW"
        kwargs = svc.files.return_value.copy.call_args.kwargs
        assert kwargs["body"] == {"name": "copy.md", "parents": ["P"]}

    async def test_copy_minimal(self, svc):
        program_files_copy(svc, {"id": "NEW", "name": "c", "mimeType": "text/plain"})
        await tools.drive_copy_file("F")
        kwargs = svc.files.return_value.copy.call_args.kwargs
        assert kwargs["body"] == {}

    async def test_safety_rail_checks_parent_when_given(self, svc_with_safety):
        svc, _ = svc_with_safety
        program_files_get(svc, {"parents": []})  # parent outside rail
        with pytest.raises(SafetyViolation):
            await tools.drive_copy_file("F", parent_id="OUTSIDE")

    async def test_safety_rail_checks_source_when_no_parent(self, svc_with_safety):
        svc, _ = svc_with_safety
        program_files_get(svc, {"parents": []})  # source outside rail
        with pytest.raises(SafetyViolation):
            await tools.drive_copy_file("F")
