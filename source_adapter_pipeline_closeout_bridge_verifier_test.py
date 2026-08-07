from __future__ import annotations

from source_adapter_pipeline_closeout_bridge import build_source_adapter_pipeline_closeout_bridge
from source_adapter_pipeline_closeout_bridge_test import fixture_archive_review_bridge
from source_adapter_pipeline_closeout_bridge_verifier import verify_source_adapter_pipeline_closeout_bridge


def test_verifier_accepts_valid_package() -> None:
    package = build_source_adapter_pipeline_closeout_bridge(fixture_archive_review_bridge())
    assert verify_source_adapter_pipeline_closeout_bridge(package)["verified"] is True


def test_verifier_rejects_bad_status() -> None:
    package = build_source_adapter_pipeline_closeout_bridge(fixture_archive_review_bridge())
    package["pipeline_closeout_bridge_status"] = "BROKEN"
    result = verify_source_adapter_pipeline_closeout_bridge(package)
    assert result["verified"] is False
    assert any("pipeline_closeout_bridge_status" in issue for issue in result["issues"])


if __name__ == "__main__":
    test_verifier_accepts_valid_package()
    test_verifier_rejects_bad_status()
    print("Source Adapter Pipeline Closeout Bridge verifier self-test passed.")
