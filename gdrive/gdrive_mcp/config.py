"""Runtime configuration (env-driven, fail-fast)."""
from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_PAGE_SIZE = 100
DRIVE_SCOPES = ("https://www.googleapis.com/auth/drive",)


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    credentials_path: str
    """Filesystem path to a Google service-account JSON key file."""

    working_folder_id: str | None
    """Optional safety rail. If set, write operations refuse to touch anything
    outside this folder (or its descendants)."""

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

        try:
            page_size = int(env.get("GDRIVE_DEFAULT_PAGE_SIZE", DEFAULT_PAGE_SIZE))
        except ValueError as exc:
            raise ConfigError(f"GDRIVE_DEFAULT_PAGE_SIZE must be numeric: {exc}") from exc

        return cls(
            credentials_path=path,
            working_folder_id=working,
            default_page_size=page_size,
        )
