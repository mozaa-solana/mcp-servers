"""Tests for the working-folder safety rail."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gdrive_mcp.safety import SafetyViolation, assert_in_working_folder


def _stub_service(parents_chain: dict[str, list[str]]) -> MagicMock:
    """Build a service stub where files().get(fileId=X) returns parents_chain[X]."""
    svc = MagicMock()

    def get_call(fileId, fields, supportsAllDrives):
        m = MagicMock()
        m.execute.return_value = {"parents": parents_chain.get(fileId, [])}
        return m

    svc.files.return_value.get.side_effect = get_call
    return svc


@pytest.mark.unit
class TestSafety:
    def test_noop_when_rail_disabled(self):
        # Rail disabled -> no service calls, no error.
        assert_in_working_folder(MagicMock(), None, "anything")

    def test_target_equals_root(self):
        assert_in_working_folder(MagicMock(), "ROOT", "ROOT")

    def test_target_is_direct_child(self):
        svc = _stub_service({"FILE": ["ROOT"]})
        assert_in_working_folder(svc, "ROOT", "FILE")

    def test_target_is_nested_descendant(self):
        svc = _stub_service(
            {
                "FILE": ["MID"],
                "MID": ["ROOT"],
            }
        )
        assert_in_working_folder(svc, "ROOT", "FILE")

    def test_outside_rail_raises(self):
        svc = _stub_service(
            {
                "FILE": ["OTHER"],
                "OTHER": [],
            }
        )
        with pytest.raises(SafetyViolation):
            assert_in_working_folder(svc, "ROOT", "FILE")

    def test_handles_orphan_chain(self):
        svc = _stub_service({"FILE": []})
        with pytest.raises(SafetyViolation):
            assert_in_working_folder(svc, "ROOT", "FILE")
