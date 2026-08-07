from __future__ import annotations

from source_pipeline_closeout import build_source_pipeline_closeout
from source_pipeline_closeout_verifier import verify_source_pipeline_closeout


def _package() -> dict:
    return {
        "archive_review_package_id": "fixture_adapter.archive_review.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "decision": "APPROVED",
        "closeout_status": "ARCHIVE_COMPLETE",
        "reviewed_receipts": [{"provider_id": "archive_today", "archive_url": "https://archive.today/example"}],
    }


def test_verifier_accepts_valid_bundle() -> None:
    bundle = build_source_pipeline_closeout(_package())
    assert verify_source_pipeline_closeout(bundle)["verified"] is True


def test_verifier_rejects_live_actions() -> None:
    bundle = build_source_pipeline_closeout(_package())
    bundle["closeout_report"]["manual_or_live_actions_started"] = True
    result = verify_source_pipeline_closeout(bundle)
    assert result["verified"] is False
    assert result["issue_count"] >= 1


def test_verifier_rejects_missing_stage() -> None:
    bundle = build_source_pipeline_closeout(_package())
    bundle["stage_inventory"]["stages"] = bundle["stage_inventory"]["stages"][:-1]
    result = verify_source_pipeline_closeout(bundle)
    assert result["verified"] is False
    assert any("15" in issue for issue in result["issues"])


if __name__ == "__main__":
    test_verifier_accepts_valid_bundle()
    test_verifier_rejects_live_actions()
    test_verifier_rejects_missing_stage()
    print("Source Pipeline Closeout verifier self-test passed.")
