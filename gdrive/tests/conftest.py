"""Shared pytest fixtures for gdrive-mcp tests.

The googleapiclient service is mocked end-to-end. Every test gets a fresh
service stub via the ``svc`` fixture; tools resolve `get_service()` lazily,
so we patch that single hook in `_registry`.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# Make the package importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _build_service_stub() -> MagicMock:
    """Build a MagicMock that mimics googleapiclient.discovery.build('drive', 'v3').

    Each resource (`files`, `revisions`, `permissions`, `about`) is a callable
    that returns a sub-mock with the relevant verbs (`list`, `get`,
    `create`, `update`, `get_media`, `export_media`). Each verb returns an
    object with `.execute()` you can configure per-test via `svc._program(...)`
    or directly via `svc.files.return_value.list.return_value.execute.return_value = ...`.
    """
    svc = MagicMock(name="DriveService")
    return svc


_TOOL_MODULES = ("about", "content", "files", "permissions", "revisions", "sheets")


def _patch_registry_everywhere(monkeypatch, cfg, drive_stub, sheets_stub):
    """Patch get_config / get_service / get_sheets_service in _registry AND
    every tool module that already imported them at module load time."""
    from gdrive_mcp.tools import _registry

    monkeypatch.setattr(_registry, "get_config", lambda: cfg)
    monkeypatch.setattr(_registry, "get_service", lambda: drive_stub)
    monkeypatch.setattr(_registry, "get_sheets_service", lambda: sheets_stub)

    for name in _TOOL_MODULES:
        mod = __import__(f"gdrive_mcp.tools.{name}", fromlist=["*"])
        if hasattr(mod, "get_config"):
            monkeypatch.setattr(mod, "get_config", lambda c=cfg: c)
        if hasattr(mod, "get_service"):
            monkeypatch.setattr(mod, "get_service", lambda s=drive_stub: s)
        if hasattr(mod, "get_sheets_service"):
            monkeypatch.setattr(mod, "get_sheets_service", lambda s=sheets_stub: s)


def _build_pair(
    monkeypatch,
    working_folder_id: str | None = None,
    local_sandbox_dir: str | None = None,
):
    from gdrive_mcp.config import Config

    fake_cfg = Config(
        credentials_path="/tmp/fake-key.json",
        working_folder_id=working_folder_id,
        local_sandbox_dir=local_sandbox_dir,
        default_page_size=100,
    )
    drive_stub = _build_service_stub()
    sheets_stub = _build_service_stub()
    _patch_registry_everywhere(monkeypatch, fake_cfg, drive_stub, sheets_stub)
    # Stash sheets stub on drive stub so `sheets_svc` fixture can find it
    # without re-running monkeypatch.
    drive_stub._sheets_stub = sheets_stub
    return drive_stub


@pytest.fixture
def svc(monkeypatch) -> MagicMock:
    """Provide a Drive service stub and patch every getter to return it."""
    return _build_pair(monkeypatch)


@pytest.fixture
def sheets_svc(svc) -> MagicMock:
    """Sheets service stub (composes with `svc` — they share monkeypatch)."""
    return svc._sheets_stub


@pytest.fixture
def svc_with_safety(monkeypatch) -> tuple[MagicMock, str]:
    """Same as `svc` but with `GDRIVE_WORKING_FOLDER_ID` set."""
    drive_stub = _build_pair(monkeypatch, working_folder_id="WORK_FOLDER")
    return drive_stub, "WORK_FOLDER"


@pytest.fixture
def sheets_svc_with_safety(svc_with_safety) -> tuple[MagicMock, MagicMock, str]:
    """(drive_stub, sheets_stub, working_folder_id) for sheets-write safety tests."""
    drive_stub, root = svc_with_safety
    return drive_stub, drive_stub._sheets_stub, root


@pytest.fixture
def svc_with_local_sandbox(monkeypatch, tmp_path) -> tuple[MagicMock, str]:
    """`svc` + `GDRIVE_LOCAL_SANDBOX_DIR` set to a tmp dir."""
    sandbox = str(tmp_path / "sandbox")
    import os

    os.makedirs(sandbox, exist_ok=True)
    drive_stub = _build_pair(monkeypatch, local_sandbox_dir=sandbox)
    return drive_stub, sandbox


def program_files_list(svc: MagicMock, payload: dict[str, Any]) -> None:
    """Helper: configure `service.files().list(...).execute()` to return *payload*."""
    svc.files.return_value.list.return_value.execute.return_value = payload


def program_files_get(svc: MagicMock, payload: dict[str, Any]) -> None:
    """Stub ``files().get(...)`` to return *payload* for **any** fileId."""
    svc.files.return_value.get.return_value.execute.return_value = payload


def program_files_get_per_id(
    svc: MagicMock, mapping: dict[str, dict[str, Any]]
) -> None:
    """Stronger sibling of :func:`program_files_get`: dispatch by ``fileId``.

    Use this when a tool issues two or more ``files().get`` calls with
    different fileIds in the same flow (e.g. metadata lookup + safety-rail
    parent walk) — a single shared payload would let bugs slip through.
    """

    def get_call(fileId, fields=None, supportsAllDrives=None, **_):
        m = MagicMock()
        m.execute.return_value = mapping.get(fileId, {})
        return m

    svc.files.return_value.get.side_effect = get_call


def program_files_create(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.files.return_value.create.return_value.execute.return_value = payload


def program_files_update(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.files.return_value.update.return_value.execute.return_value = payload


def program_about_get(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.about.return_value.get.return_value.execute.return_value = payload


def program_revisions_list(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.revisions.return_value.list.return_value.execute.return_value = payload


def program_permissions_list(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.permissions.return_value.list.return_value.execute.return_value = payload


# --------------------------------------------------------------------------
# Sheets v4 helpers
# --------------------------------------------------------------------------


def program_spreadsheet_get(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.spreadsheets.return_value.get.return_value.execute.return_value = payload


def program_values_get(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = (
        payload
    )


def program_values_batch_get(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.spreadsheets.return_value.values.return_value.batchGet.return_value.execute.return_value = (
        payload
    )


def program_values_update(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = (
        payload
    )


def program_values_append(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.spreadsheets.return_value.values.return_value.append.return_value.execute.return_value = (
        payload
    )


def program_values_clear(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.spreadsheets.return_value.values.return_value.clear.return_value.execute.return_value = (
        payload
    )


def program_values_batch_update(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.spreadsheets.return_value.values.return_value.batchUpdate.return_value.execute.return_value = (
        payload
    )


def program_structure_batch_update(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = payload


def program_sheets_copy_to(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.spreadsheets.return_value.sheets.return_value.copyTo.return_value.execute.return_value = (
        payload
    )


def program_drives_list(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.drives.return_value.list.return_value.execute.return_value = payload


def program_files_copy(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.files.return_value.copy.return_value.execute.return_value = payload
