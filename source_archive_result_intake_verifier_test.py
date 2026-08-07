from __future__ import annotations

from source_archive_result_intake_test import _handoff_package, _operator_result
from source_archive_result_intake import build_source_archive_result_intake
from source_archive_result_intake_verifier import verify_source_archive_result_intake


def test_verifier_accepts_valid_intake() -> None:
    outputs = build_source_archive_result_intake(
        archive_handoff_package=_handoff_package(),
        operator_archive_results=[_operator_result()],
    )
    verification = verify_source_archive_result_intake(
        outputs.archive_result_intake_record,
        outputs.archive_receipt_index,
        outputs.archive_review_handoff,
    )
    assert verification["verified"] is True
    assert verification["issue_count"] == 0


def test_verifier_rejects_online_validation_claim() -> None:
    outputs = build_source_archive_result_intake(
        archive_handoff_package=_handoff_package(),
        operator_archive_results=[_operator_result()],
    )
    record = dict(outputs.archive_result_intake_record)
    record["online_validation_performed"] = True
    verification = verify_source_archive_result_intake(record, outputs.archive_receipt_index, outputs.archive_review_handoff)
    assert verification["verified"] is False
    assert any("online validation" in issue for issue in verification["issues"])


if __name__ == "__main__":
    test_verifier_accepts_valid_intake()
    test_verifier_rejects_online_validation_claim()
    print("Source Archive Result Intake verifier self-test passed.")
