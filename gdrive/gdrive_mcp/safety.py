"""Working-folder safety rail.

When ``GDRIVE_WORKING_FOLDER_ID`` is set, every write tool refuses to act on
files outside the configured folder (or its descendants). The rail is a
defense-in-depth measure for early users who don't yet have a strong sense of
how an agent might misuse Drive write access.
"""
from __future__ import annotations

from typing import Any


class SafetyViolation(RuntimeError):
    """Raised when a write target is outside the configured working folder."""


def assert_in_working_folder(
    service: Any, working_folder_id: str | None, target_id: str
) -> None:
    """Raise :class:`SafetyViolation` if *target_id* is not the working folder
    nor a descendant of it.

    No-op when *working_folder_id* is ``None``.

    *target_id* is the file/folder the caller is about to mutate (or for
    ``create``, the parent folder being created into).
    """
    if not working_folder_id:
        return
    if target_id == working_folder_id:
        return

    seen: set[str] = set()
    cur = target_id
    while cur and cur not in seen:
        seen.add(cur)
        meta = (
            service.files()
            .get(fileId=cur, fields="parents", supportsAllDrives=True)
            .execute()
        )
        parents = meta.get("parents") or []
        if working_folder_id in parents:
            return
        cur = parents[0] if parents else None

    raise SafetyViolation(
        f"target {target_id} is outside working folder {working_folder_id}; "
        "unset GDRIVE_WORKING_FOLDER_ID to disable the rail"
    )
