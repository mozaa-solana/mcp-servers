"""Runtime configuration (env-driven, fail-fast)."""
from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_PAGE_SIZE = 100
# `drive` covers Sheets-via-Drive access; `spreadsheets` is added explicitly
# so the Sheets API treats us as authorized regardless of file ownership.
DRIVE_SCOPES = (
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
)


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    credentials_path: str
    """Filesystem path to a Google service-account JSON key file."""

    working_folder_id: str | None
    """Optional Drive safety rail. If set, write operations refuse to touch
    anything outside this folder (or its descendants)."""

    local_sandbox_dir: str | None
    """Optional local-disk safety rail. If set, every tool that reads/writes a
    local path (``drive_upload_file``, ``drive_export_file``) refuses paths
    that resolve outside this directory (path-traversal protection)."""

    default_page_size: int

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Config":
        env = env if env is not None else dict(os.environ)
        # Standard Google env var first, fall back to project-specific.
        path = (
            env.get("GOOGLE_APPLICATION_CREDENTIALS")
            or env.get("GDRIVE_SERVICE_ACCOUNT_JSON")
            or ""
        ).strip()
        if not path:
            raise ConfigError(
                "GOOGLE_APPLICATION_CREDENTIALS (or GDRIVE_SERVICE_ACCOUNT_JSON) "
                "must point to a service-account JSON key file"
            )
        if not os.path.isfile(path):
            raise ConfigError(f"service-account key file not found: {path}")

        working = (env.get("GDRIVE_WORKING_FOLDER_ID") or "").strip() or None

        sandbox = (env.get("GDRIVE_LOCAL_SANDBOX_DIR") or "").strip() or None
        if sandbox and not os.path.isdir(sandbox):
            raise ConfigError(
                f"GDRIVE_LOCAL_SANDBOX_DIR must be an existing directory: {sandbox}"
            )

        try:
            page_size = int(env.get("GDRIVE_DEFAULT_PAGE_SIZE", DEFAULT_PAGE_SIZE))
        except ValueError as exc:
            raise ConfigError(f"GDRIVE_DEFAULT_PAGE_SIZE must be numeric: {exc}") from exc

        return cls(
            credentials_path=path,
            working_folder_id=working,
            local_sandbox_dir=sandbox,
            default_page_size=page_size,
        )
