from __future__ import annotations

import tempfile
from pathlib import Path

from source_msn_adapter_maintenance_guard import (
    CORE_ARTIFACTS,
    GuardArtifact,
    build_maintenance_guard,
    write_report,
)


def test_guard_reports_present_and_missing_artifacts() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        artifacts = [
            GuardArtifact("present.py", "demo", True, "present file"),
            GuardArtifact("missing.py", "demo", True, "missing file"),
            GuardArtifact("optional.md", "demo", False, "optional file"),
        ]
        (root / "present.py").write_text("x=1\n", encoding="utf-8")
        report = build_maintenance_guard(root, artifacts=artifacts)
        assert report.status == "MAINTENANCE_GUARD_FAIL"
        assert report.required_present == 1
        assert report.required_missing == 1
        assert report.optional_missing == 1


def test_guard_writes_json_markdown_csv() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        artifacts = [GuardArtifact("present.py", "demo", True, "present file")]
        (root / "present.py").write_text("x=1\n", encoding="utf-8")
        report = build_maintenance_guard(root, artifacts=artifacts)
        outputs = write_report(report, root / "out")
        for p in outputs.values():
            assert Path(p).exists()
        assert report.status == "READY_FOR_LIVE_EVIDENCE"


def test_core_artifact_list_contains_live_boundary_components() -> None:
    names = {a.path for a in CORE_ARTIFACTS}
    assert "source_msn_adapter_live_evidence_validator.py" in names
    assert "source_msn_adapter_release_promotion.py" in names
    assert "MSN_SOURCE_ADAPTER_STATUS_WORDING_LOCK.md" in names
    assert "MSN_SOURCE_ADAPTER_FINAL_HANDOFF_LOCK.md" in names


if __name__ == "__main__":
    test_guard_reports_present_and_missing_artifacts()
    test_guard_writes_json_markdown_csv()
    test_core_artifact_list_contains_live_boundary_components()
    print("MSN maintenance guard self-test passed.")
