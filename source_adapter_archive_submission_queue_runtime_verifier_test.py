from __future__ import annotations

from source_adapter_archive_submission_queue_runtime import build_package
from source_adapter_archive_submission_queue_runtime_verifier import verify_archive_submission_queue_runtime_package


def test_archive_submission_queue_runtime_verifier() -> None:
    package = build_package(operator_id="verifier_operator")
    result = verify_archive_submission_queue_runtime_package(package)
    assert result["verified"] is True
    package["keys_accounts_label"] = "KEYS"
    result = verify_archive_submission_queue_runtime_package(package)
    assert result["verified"] is False
    assert "keys_accounts_label_mismatch" in result["issues"]


if __name__ == "__main__":
    test_archive_submission_queue_runtime_verifier()
    print("Source Adapter Archive Submission Queue Runtime verifier self-test passed.")
