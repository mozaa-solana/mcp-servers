"""Tests for drive_client.wrap_http_error + handle_drive_errors decorator."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from gdrive_mcp.drive_client import DriveAPIError, wrap_http_error


def _make_http_error(status: int, reason: str = "Test", body: bytes = b'{"error":"x"}'):
    resp = MagicMock()
    resp.status = status
    resp.reason = reason
    return HttpError(resp, body)


@pytest.mark.unit
class TestWrapHttpError:
    def test_preserves_status_code(self):
        err = _make_http_error(404, "Not Found")
        wrapped = wrap_http_error(err)
        assert isinstance(wrapped, DriveAPIError)
        assert wrapped.status_code == 404
        assert wrapped.reason == "Not Found"

    def test_handles_403(self):
        err = _make_http_error(403)
        wrapped = wrap_http_error(err)
        assert wrapped.status_code == 403

    def test_handles_429_rate_limit(self):
        err = _make_http_error(429, "Too Many Requests")
        wrapped = wrap_http_error(err)
        assert wrapped.status_code == 429

    def test_handles_non_int_status(self):
        resp = MagicMock()
        resp.status = "weird"
        resp.reason = "??"
        err = HttpError(resp, b"")
        wrapped = wrap_http_error(err)
        assert wrapped.status_code == 0


@pytest.mark.asyncio
@pytest.mark.unit
class TestHandleDriveErrorsDecorator:
    async def test_http_error_becomes_error_dict(self, svc):
        """Tools wrapped by handle_drive_errors must convert HttpError → dict.

        The previous version of the codebase let HttpError propagate as a raw
        traceback through MCP — this regression test prevents that.
        """
        from gdrive_mcp.tools import about as tools

        # Make about().get().execute() raise.
        svc.about.return_value.get.return_value.execute.side_effect = (
            _make_http_error(403, "Forbidden", b'{"error":"insufficient permissions"}')
        )

        out = await tools.drive_about()
        assert "error" in out
        assert out.get("status_code") == 403

    async def test_404_propagates_status(self, svc):
        from gdrive_mcp.tools import files as tools

        svc.files.return_value.get.return_value.execute.side_effect = (
            _make_http_error(404, "Not Found")
        )
        out = await tools.drive_get_metadata("DOES_NOT_EXIST")
        assert out.get("status_code") == 404

    async def test_safety_violation_becomes_dict_with_kind(self, svc_with_safety):
        """SafetyViolation should also be caught and labelled."""
        from gdrive_mcp.tools import files as tools
        from tests.conftest import program_files_get

        svc, _ = svc_with_safety
        program_files_get(svc, {"parents": []})  # outside rail

        out = await tools.drive_rename_file("F", "new")
        assert out.get("violation") == "working_folder"
        assert "outside working folder" in out["error"]
