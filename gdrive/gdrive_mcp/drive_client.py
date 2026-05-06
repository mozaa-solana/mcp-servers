"""Drive service factory + error mapping.

Keeps the only googleapiclient import in one place so tests can patch it
cleanly and so future swaps (OAuth user-flow, custom transport) only touch
this module.
"""
from __future__ import annotations

from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import DRIVE_SCOPES, Config


class DriveAPIError(RuntimeError):
    """Wrapper around :class:`googleapiclient.errors.HttpError`."""

    def __init__(self, status_code: int, reason: str, body: Any) -> None:
        self.status_code = status_code
        self.reason = reason
        self.body = body
        super().__init__(f"Drive API {status_code} {reason}: {body!r}")


def build_service(config: Config) -> Any:
    """Construct a Drive v3 service client from a Config."""
    creds = service_account.Credentials.from_service_account_file(
        config.credentials_path, scopes=list(DRIVE_SCOPES)
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def wrap_http_error(exc: HttpError) -> DriveAPIError:
    """Convert googleapiclient HttpError into a domain error type."""
    status = getattr(exc.resp, "status", 0) if hasattr(exc, "resp") else 0
    reason = getattr(exc.resp, "reason", "") if hasattr(exc, "resp") else ""
    try:
        body = exc.error_details or exc.reason
    except Exception:
        body = str(exc)
    return DriveAPIError(int(status or 0), str(reason), body)
