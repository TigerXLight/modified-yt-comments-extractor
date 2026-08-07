from __future__ import annotations

from source_total_export_package import build_source_total_export_package
from source_total_export_package_test import _fixture_capture_bundle
from source_total_export_package_verifier import verify_source_total_export_package


def test_verifier_accepts_valid_package() -> None:
    package = build_source_total_export_package(capture_bundle=_fixture_capture_bundle()).total_export_package
    result = verify_source_total_export_package(package)
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_verifier_rejects_missing_status() -> None:
    package = build_source_total_export_package(capture_bundle=_fixture_capture_bundle()).total_export_package
    package["export_status"] = "DRAFT"
    result = verify_source_total_export_package(package)
    assert result["verified"] is False
    assert any("READY_FOR_EVIDENCE_QUEUE" in issue for issue in result["issues"])


if __name__ == "__main__":
    test_verifier_accepts_valid_package()
    test_verifier_rejects_missing_status()
    print("Source Total Export package verifier self-test passed.")
