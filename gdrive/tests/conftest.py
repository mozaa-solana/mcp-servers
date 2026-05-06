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


_TOOL_MODULES = ("about", "content", "files", "permissions", "revisions")


def _patch_registry_everywhere(monkeypatch, cfg, stub):
    """Patch get_config / get_service in _registry AND every tool module that
    already imported them at module load time."""
    from gdrive_mcp.tools import _registry

    monkeypatch.setattr(_registry, "get_config", lambda: cfg)
    monkeypatch.setattr(_registry, "get_service", lambda: stub)

    for name in _TOOL_MODULES:
        mod = __import__(f"gdrive_mcp.tools.{name}", fromlist=["*"])
        if hasattr(mod, "get_config"):
            monkeypatch.setattr(mod, "get_config", lambda c=cfg: c)
        if hasattr(mod, "get_service"):
            monkeypatch.setattr(mod, "get_service", lambda s=stub: s)


@pytest.fixture
def svc(monkeypatch) -> MagicMock:
    """Provide a Drive service stub and patch :func:`get_service` to return it."""
    from gdrive_mcp.config import Config

    fake_cfg = Config(
        credentials_path="/tmp/fake-key.json",
        working_folder_id=None,
        default_page_size=100,
    )
    stub = _build_service_stub()
    _patch_registry_everywhere(monkeypatch, fake_cfg, stub)
    return stub


@pytest.fixture
def svc_with_safety(monkeypatch) -> tuple[MagicMock, str]:
    """Same as `svc` but with `GDRIVE_WORKING_FOLDER_ID` set."""
    from gdrive_mcp.config import Config

    fake_cfg = Config(
        credentials_path="/tmp/fake-key.json",
        working_folder_id="WORK_FOLDER",
        default_page_size=100,
    )
    stub = _build_service_stub()
    _patch_registry_everywhere(monkeypatch, fake_cfg, stub)
    return stub, "WORK_FOLDER"


def program_files_list(svc: MagicMock, payload: dict[str, Any]) -> None:
    """Helper: configure `service.files().list(...).execute()` to return *payload*."""
    svc.files.return_value.list.return_value.execute.return_value = payload


def program_files_get(svc: MagicMock, payload: dict[str, Any]) -> None:
    svc.files.return_value.get.return_value.execute.return_value = payload


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
