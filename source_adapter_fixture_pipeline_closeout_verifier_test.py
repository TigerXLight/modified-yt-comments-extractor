from __future__ import annotations

from source_adapter_fixture_pipeline_closeout import build_source_adapter_fixture_pipeline_closeout
from source_adapter_fixture_pipeline_closeout_test import _passed_pipeline
from source_adapter_fixture_pipeline_closeout_verifier import verify_source_adapter_fixture_pipeline_closeout


def test_verifier_accepts_valid_closeout() -> None:
    package = build_source_adapter_fixture_pipeline_closeout(_passed_pipeline())
    result = verify_source_adapter_fixture_pipeline_closeout(package)
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_verifier_rejects_closed_non_passed_pipeline() -> None:
    package = build_source_adapter_fixture_pipeline_closeout(_passed_pipeline())
    package["fixture_pipeline_status"] = "FAILED"
    result = verify_source_adapter_fixture_pipeline_closeout(package)
    assert result["verified"] is False
    assert any("PASSED" in issue for issue in result["issues"])


if __name__ == "__main__":
    test_verifier_accepts_valid_closeout()
    test_verifier_rejects_closed_non_passed_pipeline()
    print("Source Adapter Fixture Pipeline Closeout verifier self-test passed.")
