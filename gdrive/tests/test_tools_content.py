"""Tests for tools/content.py — smart export, upload, create, update, export."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gdrive_mcp.normalize import GOOGLE_DOC, GOOGLE_SHEET
from gdrive_mcp.safety import SafetyViolation
from gdrive_mcp.tools import content as tools
from tests.conftest import program_files_create, program_files_get, program_files_update


def _program_export(svc: MagicMock, payload: bytes) -> None:
    svc.files.return_value.export_media.return_value.execute.return_value = payload


def _program_get_media(svc: MagicMock, payload: bytes) -> None:
    svc.files.return_value.get_media.return_value.execute.return_value = payload


# --------------------------------------------------------------------------
# drive_get_content
# --------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetContent:
    async def test_google_doc_default_export_markdown(self, svc):
        program_files_get(svc, {"name": "doc", "mimeType": GOOGLE_DOC})
        _program_export(svc, b"# heading\n\nbody")
        out = await tools.drive_get_content("F")
        assert out["exported_as"] == "text/markdown"
        assert out["content"].startswith("# heading")
        assert out["truncated"] is False

    async def test_google_sheet_default_csv(self, svc):
        program_files_get(svc, {"name": "s", "mimeType": GOOGLE_SHEET})
        _program_export(svc, b"a,b,c\n1,2,3\n")
        out = await tools.drive_get_content("S")
        assert out["exported_as"] == "text/csv"
        assert "a,b,c" in out["content"]

    async def test_google_doc_custom_export(self, svc):
        program_files_get(svc, {"name": "d", "mimeType": GOOGLE_DOC})
        _program_export(svc, b"plain")
        out = await tools.drive_get_content("D", export_mime="text/plain")
        assert out["exported_as"] == "text/plain"

    async def test_text_file_downloaded_inline(self, svc):
        program_files_get(svc, {"name": "x.md", "mimeType": "text/markdown"})
        _program_get_media(svc, b"hello")
        out = await tools.drive_get_content("X")
        assert out["content"] == "hello"
        assert out.get("exported_as") is None

    async def test_binary_rejected_with_hint(self, svc):
        program_files_get(svc, {"name": "img", "mimeType": "image/png"})
        out = await tools.drive_get_content("X")
        assert "drive_export_file" in out["error"]

    async def test_truncates_when_too_large(self, svc, monkeypatch):
        monkeypatch.setattr(tools, "MAX_INLINE_BYTES", 5)
        program_files_get(svc, {"name": "x.md", "mimeType": "text/markdown"})
        _program_get_media(svc, b"abcdefghij")
        out = await tools.drive_get_content("X")
        assert out["truncated"] is True
        assert len(out["content"]) <= 5


# --------------------------------------------------------------------------
# drive_export_file (download to disk)
# --------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
class TestExportFile:
    async def test_writes_native_export(self, svc, tmp_path):
        program_files_get(svc, {"name": "doc", "mimeType": GOOGLE_DOC})
        _program_export(svc, b"%PDF-fake-bytes")
        target = tmp_path / "out.pdf"
        out = await tools.drive_export_file("D", "application/pdf", str(target))
        assert target.read_bytes() == b"%PDF-fake-bytes"
        assert out["bytes_written"] == 15
        assert out["exported_as"] == "application/pdf"

    async def test_writes_binary_via_get_media(self, svc, tmp_path):
        program_files_get(svc, {"name": "img.png", "mimeType": "image/png"})
        _program_get_media(svc, b"\x89PNG")
        target = tmp_path / "out.png"
        out = await tools.drive_export_file("X", "image/png", str(target))
        assert target.read_bytes() == b"\x89PNG"
        assert out["exported_as"] is None

    async def test_rejects_missing_parent_dir(self, svc):
        program_files_get(svc, {"name": "x", "mimeType": "text/plain"})
        out = await tools.drive_export_file("X", "text/plain", "/no/such/dir/x.txt")
        assert "parent directory" in out["error"]


# --------------------------------------------------------------------------
# Write
# --------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
class TestUploadFile:
    async def test_rejects_missing_local_file(self, svc):
        out = await tools.drive_upload_file("/no/such/file.txt", parent_id="P")
        assert "local file not found" in out["error"]

    async def test_uploads_file(self, svc, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("hi")
        program_files_create(svc, {"id": "F", "name": "x.txt", "mimeType": "text/plain"})
        out = await tools.drive_upload_file(str(f))
        assert out["id"] == "F"

    async def test_safety_rail_requires_parent(self, svc_with_safety, tmp_path):
        svc, _ = svc_with_safety
        f = tmp_path / "x.txt"
        f.write_text("hi")
        out = await tools.drive_upload_file(str(f))
        assert "GDRIVE_WORKING_FOLDER_ID" in out["error"]

    async def test_safety_rail_blocks_outside_parent(self, svc_with_safety, tmp_path):
        svc, _ = svc_with_safety
        f = tmp_path / "x.txt"
        f.write_text("hi")
        program_files_get(svc, {"parents": []})  # outside rail
        with pytest.raises(SafetyViolation):
            await tools.drive_upload_file(str(f), parent_id="OUTSIDE")


@pytest.mark.asyncio
@pytest.mark.unit
class TestCreateTextFile:
    async def test_creates_with_default_mime(self, svc):
        program_files_create(svc, {"id": "F", "name": "n", "mimeType": "text/plain"})
        out = await tools.drive_create_text_file("n", "hello")
        assert out["id"] == "F"

    async def test_safety_rail_requires_parent(self, svc_with_safety):
        out = await tools.drive_create_text_file("n", "hello")
        assert "GDRIVE_WORKING_FOLDER_ID" in out["error"]


@pytest.mark.asyncio
@pytest.mark.unit
class TestUpdateContent:
    async def test_updates_existing(self, svc):
        program_files_update(svc, {"id": "F", "name": "n", "mimeType": "text/plain"})
        out = await tools.drive_update_file_content("F", "new")
        assert out["id"] == "F"

    async def test_safety_rail_blocks_outside(self, svc_with_safety):
        svc, _ = svc_with_safety
        program_files_get(svc, {"parents": []})
        with pytest.raises(SafetyViolation):
            await tools.drive_update_file_content("F", "x")
