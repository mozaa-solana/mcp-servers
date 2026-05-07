"""Safety rails for write operations.

Two independent rails:
  • **Working folder rail** (`GDRIVE_WORKING_FOLDER_ID`) — confines mutations
    inside Drive to a single folder (and its descendants).
  • **Local sandbox rail** (`GDRIVE_LOCAL_SANDBOX_DIR`) — confines local-disk
    reads/writes (`drive_upload_file`, `drive_export_file`) to a single
    directory, blocking path-traversal abuse.

Both rails are no-ops when the corresponding env var is unset.
"""
from __future__ import annotations

import os
from collections import deque
from typing import Any


class SafetyViolation(RuntimeError):
    """Raised when a write target is outside the configured working folder."""


class LocalPathViolation(RuntimeError):
    """Raised when a local filesystem path escapes the configured sandbox."""


# --------------------------------------------------------------------------
# Drive working-folder rail
# --------------------------------------------------------------------------


def assert_in_working_folder(
    service: Any, working_folder_id: str | None, target_id: str
) -> None:
    """Raise :class:`SafetyViolation` if *target_id* is not the working folder
    nor a descendant of it.

    Walks **all** parents (Drive permits a file to have multiple parents
    inside the same Shared Drive). Returns as soon as any path reaches the
    working folder.
    """
    if not working_folder_id:
        return
    if target_id == working_folder_id:
        return

    seen: set[str] = set()
    queue: deque[str] = deque([target_id])
    while queue:
        cur = queue.popleft()
        if cur in seen:
            continue
        seen.add(cur)
        meta = (
            service.files()
            .get(fileId=cur, fields="parents", supportsAllDrives=True)
            .execute()
        )
        parents = meta.get("parents") or []
        if working_folder_id in parents:
            return
        for p in parents:
            if p not in seen:
                queue.append(p)

    raise SafetyViolation(
        f"target {target_id} is outside working folder {working_folder_id}; "
        "unset GDRIVE_WORKING_FOLDER_ID to disable the rail"
    )


# --------------------------------------------------------------------------
# Local-disk sandbox rail
# --------------------------------------------------------------------------


def assert_in_local_sandbox(sandbox_dir: str | None, path: str) -> None:
    """Raise :class:`LocalPathViolation` if *path* (a local filesystem path
    used for upload/export) escapes the configured sandbox directory.

    Resolves symlinks via ``os.path.realpath`` and checks that the canonical
    target lives under the canonical sandbox. No-op when *sandbox_dir* is
    unset.
    """
    if not sandbox_dir:
        return

    real_sandbox = os.path.realpath(sandbox_dir)
    real_target = os.path.realpath(os.path.abspath(path))

    if not os.path.isdir(real_sandbox):
        raise LocalPathViolation(
            f"GDRIVE_LOCAL_SANDBOX_DIR points to a non-directory: {sandbox_dir}"
        )

    try:
        common = os.path.commonpath([real_target, real_sandbox])
    except ValueError:
        # Different drives on Windows, or relative-vs-absolute mix.
        raise LocalPathViolation(
            f"path {path} cannot be compared against sandbox {sandbox_dir}"
        )

    if common != real_sandbox:
        raise LocalPathViolation(
            f"local path {path} (resolved to {real_target}) is outside "
            f"sandbox {real_sandbox}; unset GDRIVE_LOCAL_SANDBOX_DIR to disable"
        )
