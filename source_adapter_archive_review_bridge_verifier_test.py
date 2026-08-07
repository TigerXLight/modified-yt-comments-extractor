from __future__ import annotations

from source_adapter_archive_review_bridge import build_source_adapter_archive_review_bridge
from source_adapter_archive_review_bridge_test import fixture_archive_result_intake_bridge
from source_adapter_archive_review_bridge_verifier import verify_source_adapter_archive_review_bridge


def main() -> None:
    package = build_source_adapter_archive_review_bridge(
        fixture_archive_result_intake_bridge(),
        archive_reviewer_decision={"decision": "APPROVED"},
    )
    verification = verify_source_adapter_archive_review_bridge(package)
    assert verification["schema_version"] == "source_adapter_archive_review_bridge_verifier_v1"
    assert verification["verified"] is True
    assert verification["issue_count"] == 0
    blocked = dict(package)
    blocked["source_adapter_pipeline_closeout_batch_handoff"] = dict(package["source_adapter_pipeline_closeout_batch_handoff"], ready_for_pipeline_closeout=False)
    assert verify_source_adapter_archive_review_bridge(blocked)["verified"] is False


if __name__ == "__main__":
    main()
    print("Source Adapter Archive Review Bridge verifier self-test passed.")
