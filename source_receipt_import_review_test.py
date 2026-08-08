from __future__ import annotations

from source_receipt_import_review import (
    attach_receipt_reviews_to_workflow_summary,
    build_source_receipt_import_review_bundle,
    import_source_receipt_payload,
)


def _valid_receipt(receipt_type: str = "article_page") -> dict[str, object]:
    return {
        "receipt_type": receipt_type,
        "method_id": "generic_article_html",
        "operator_timestamp_utc": "2026-08-08T00:00:00Z",
        "status": "completed_manually",
        "artifact_count": 2,
        "hashes": ["a" * 64],
    }


def test_import_valid_receipt_metadata_only() -> None:
    receipt = import_source_receipt_payload(_valid_receipt())
    data = receipt.to_dict()

    assert data["accepted"] is True
    assert data["user_review_required"] is True
    assert data["safe_metadata"]["artifact_count"] == 2
    assert data["safe_metadata"]["hash_count"] == 1


def test_receipt_import_rejects_credentials_raw_payload_and_full_paths() -> None:
    payload = _valid_receipt("comments")
    payload.update(
        {
            "cookies": "secret",
            "raw_payload": {"text": "do not import raw payload"},
            "artifact_path": "C:\\Users\\fahad\\secret.txt",
        }
    )
    receipt = import_source_receipt_payload(payload)

    assert receipt.accepted is False
    assert any(error.startswith("unsafe_key:") for error in receipt.validation_errors)
    assert any(error.startswith("full_local_path_rejected:") for error in receipt.validation_errors)


def test_receipt_import_rejects_unsafe_claims() -> None:
    payload = _valid_receipt("archive")
    payload["archive_submission_claimed"] = True
    payload["automatic_classification"] = True
    receipt = import_source_receipt_payload(payload)

    assert receipt.accepted is False
    assert "unsafe_claim:archive_submission_claimed" in receipt.validation_errors
    assert "unsafe_claim:automatic_classification" in receipt.validation_errors


def test_completed_evidence_requires_completed_receipt_type_and_hash() -> None:
    wrong_type = _valid_receipt("media")
    wrong_type["completed_evidence_claimed"] = True
    receipt = import_source_receipt_payload(wrong_type)
    assert "completed_evidence_claim_wrong_receipt_type" in receipt.validation_errors

    missing_hash = _valid_receipt("completed_evidence")
    missing_hash["completed_evidence_claimed"] = True
    missing_hash.pop("hashes")
    missing_hash.pop("verified_sha256", None)
    missing_hash_receipt = import_source_receipt_payload(missing_hash)
    assert "completed_evidence_requires_verified_hash" in missing_hash_receipt.validation_errors


def test_receipt_review_bundle_attaches_to_workflow_summary() -> None:
    bundle = build_source_receipt_import_review_bundle(
        (
            _valid_receipt("screenshot"),
            {"receipt_type": "unknown", "status": "bad"},
        )
    )
    summary = attach_receipt_reviews_to_workflow_summary(
        source_id="source_row_1",
        bundle=bundle,
    )

    assert bundle.receipt_count == 2
    assert bundle.accepted_count == 1
    assert bundle.rejected_count == 1
    assert summary["receipt_import_bundle_id"] == bundle.bundle_id
    assert summary["user_review_required"] is True
    assert summary["live_execution_performed_by_importer"] is False


if __name__ == "__main__":
    test_import_valid_receipt_metadata_only()
    test_receipt_import_rejects_credentials_raw_payload_and_full_paths()
    test_receipt_import_rejects_unsafe_claims()
    test_completed_evidence_requires_completed_receipt_type_and_hash()
    test_receipt_review_bundle_attaches_to_workflow_summary()
