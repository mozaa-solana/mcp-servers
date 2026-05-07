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

    def test_multi_parent_one_inside_rail_passes(self):
        """A file with parents=[OUTSIDE, INSIDE] must pass when INSIDE is the rail."""
        svc = _stub_service(
            {
                "FILE": ["OUTSIDE", "INSIDE_INTERMEDIATE"],
                "OUTSIDE": [],  # dead end on this branch
                "INSIDE_INTERMEDIATE": ["ROOT"],
            }
        )
        # Bug guard: a single-parent walk that always followed parents[0] would
        # descend into OUTSIDE first and eventually raise.
        assert_in_working_folder(svc, "ROOT", "FILE")

    def test_multi_parent_root_itself_in_parents(self):
        svc = _stub_service({"FILE": ["OTHER", "ROOT"]})
        assert_in_working_folder(svc, "ROOT", "FILE")


@pytest.mark.unit
class TestLocalSandbox:
    def test_noop_when_disabled(self, tmp_path):
        # Path doesn't matter — rail off
        from gdrive_mcp.safety import assert_in_local_sandbox

        assert_in_local_sandbox(None, "/etc/passwd")

    def test_path_inside_sandbox_passes(self, tmp_path):
        from gdrive_mcp.safety import assert_in_local_sandbox

        target = tmp_path / "child.txt"
        target.write_text("x")
        assert_in_local_sandbox(str(tmp_path), str(target))

    def test_nested_path_passes(self, tmp_path):
        from gdrive_mcp.safety import assert_in_local_sandbox

        nested = tmp_path / "a" / "b" / "c.txt"
        nested.parent.mkdir(parents=True)
        nested.write_text("x")
        assert_in_local_sandbox(str(tmp_path), str(nested))

    def test_path_outside_sandbox_raises(self, tmp_path):
        from gdrive_mcp.safety import LocalPathViolation, assert_in_local_sandbox

        with pytest.raises(LocalPathViolation):
            assert_in_local_sandbox(str(tmp_path), "/etc/passwd")

    def test_traversal_with_dotdot_resolved_and_rejected(self, tmp_path):
        from gdrive_mcp.safety import LocalPathViolation, assert_in_local_sandbox

        sneaky = str(tmp_path / ".." / "outside.txt")
        with pytest.raises(LocalPathViolation):
            assert_in_local_sandbox(str(tmp_path), sneaky)

    def test_symlink_escape_rejected(self, tmp_path):
        """A symlink inside the sandbox pointing outside should be caught
        because we use ``realpath``."""
        from gdrive_mcp.safety import LocalPathViolation, assert_in_local_sandbox

        outside = tmp_path.parent / "external.txt"
        outside.write_text("secret")
        link = tmp_path / "innocent.txt"
        link.symlink_to(outside)
        with pytest.raises(LocalPathViolation):
            assert_in_local_sandbox(str(tmp_path), str(link))

    def test_nonexistent_sandbox_raises(self, tmp_path):
        from gdrive_mcp.safety import LocalPathViolation, assert_in_local_sandbox

        with pytest.raises(LocalPathViolation):
            assert_in_local_sandbox(str(tmp_path / "nonexistent"), "x")
