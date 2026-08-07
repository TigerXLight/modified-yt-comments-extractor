from __future__ import annotations

from source_adapter_coverage_acceptance import build_source_adapter_coverage_acceptance
from source_adapter_coverage_acceptance_test import _accepted_closeout
from source_adapter_coverage_acceptance_verifier import verify_source_adapter_coverage_acceptance


def test_verifier_accepts_valid_package() -> None:
    package = build_source_adapter_coverage_acceptance(_accepted_closeout())
    report = verify_source_adapter_coverage_acceptance(package)
    assert report["verified"] is True
    assert report["issue_count"] == 0


def test_verifier_rejects_mismatched_record() -> None:
    package = build_source_adapter_coverage_acceptance(_accepted_closeout())
    package["acceptance_record"]["source_adapter_coverage_acceptance_id"] = "wrong"
    report = verify_source_adapter_coverage_acceptance(package)
    assert report["verified"] is False
    assert any("acceptance_record" in issue for issue in report["issues"])


if __name__ == "__main__":
    test_verifier_accepts_valid_package()
    test_verifier_rejects_mismatched_record()
    print("Source Adapter Coverage Acceptance verifier self-test passed.")
