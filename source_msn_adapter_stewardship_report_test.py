from __future__ import annotations

import tempfile
from pathlib import Path

import source_msn_adapter_maintenance_guard as guard
from source_msn_adapter_maintenance_guard import GuardArtifact
from source_msn_adapter_stewardship_report import build_stewardship_report, write_stewardship_report


def test_stewardship_report_ready_when_required_artifacts_exist() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        original = guard.CORE_ARTIFACTS
        try:
            guard.CORE_ARTIFACTS = [GuardArtifact("a.py", "demo", True, "a")]
            (root / "a.py").write_text("x=1\n", encoding="utf-8")
            report = build_stewardship_report(root, root / "out")
            assert report.status == "READY_FOR_LIVE_EVIDENCE"
            assert report.final_live_state_allowed == "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"
            outputs = write_stewardship_report(report, root / "out")
            assert Path(outputs["json"]).exists()
            assert Path(outputs["markdown"]).exists()
        finally:
            guard.CORE_ARTIFACTS = original


def test_stewardship_report_blocks_when_required_artifact_missing() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        original = guard.CORE_ARTIFACTS
        try:
            guard.CORE_ARTIFACTS = [GuardArtifact("missing.py", "demo", True, "missing")]
            report = build_stewardship_report(root, root / "out")
            assert report.status == "BLOCKED_BY_MISSING_REPO_ARTIFACTS"
            assert "Restore missing" in report.next_action
        finally:
            guard.CORE_ARTIFACTS = original


if __name__ == "__main__":
    test_stewardship_report_ready_when_required_artifacts_exist()
    test_stewardship_report_blocks_when_required_artifact_missing()
    print("MSN stewardship report self-test passed.")
