import json
from pathlib import Path
from tempfile import TemporaryDirectory

from evidence_item_queue import EvidenceItemQueue, EvidenceItemRole, EvidenceItemStatus, EvidenceQueueItem
from evidence_item_queue_store import (
    build_evidence_item_queue_review_store_document,
    read_evidence_item_queue_review_store,
    validate_evidence_item_queue_review_store_document,
    write_evidence_item_queue_review_store,
)


def _queue_with_sensitive_path() -> EvidenceItemQueue:
    return EvidenceItemQueue(
        items=(
            EvidenceQueueItem(
                item_id="local_media_1",
                item_role=EvidenceItemRole.LOCAL_MEDIA,
                display_name="sample.mp4",
                local_path=r"C:\Users\fahad\Secret Folder\sample.mp4",
                file_hash="a" * 64,
                item_status=EvidenceItemStatus.NEEDS_REVIEW,
                total_export_include=True,
                created_at_utc="2026-08-06T12:00:00Z",
                updated_at_utc="2026-08-06T12:00:00Z",
            ),
        )
    )


def run_self_test() -> None:
    queue = _queue_with_sensitive_path()
    document = build_evidence_item_queue_review_store_document(
        queue,
        session_id="queue-store-test",
        timestamp_utc="2026-08-06T12:00:00Z",
    )
    document_dict = document.to_dict()
    validate_evidence_item_queue_review_store_document(document_dict)
    encoded = json.dumps(document_dict, sort_keys=True)
    assert r"C:\Users\fahad" not in encoded
    assert "sample.mp4" not in encoded
    assert document_dict["queue_review_summary"]["local_path_recorded_count"] == 1
    assert document_dict["queue_review_summary"]["file_hash_recorded_count"] == 1
    assert document_dict["activity_flow_summary"]["file_existence_claimed"] is False
    assert document_dict["full_local_path_included"] is False
    assert document_dict["completed_evidence_claimed"] is False

    repeated = build_evidence_item_queue_review_store_document(
        queue,
        session_id="queue-store-test",
        timestamp_utc="2026-08-06T12:00:00Z",
    )
    assert repeated.to_dict() == document_dict

    with TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "queue_review_store.json"
        written = write_evidence_item_queue_review_store(document, output_path)
        assert written == str(output_path)
        assert output_path.is_file()
        assert list(Path(temp_dir).glob("*.tmp")) == []
        loaded = read_evidence_item_queue_review_store(output_path)
        assert loaded == document_dict

        tampered = dict(loaded)
        tampered["file_move_performed"] = True
        try:
            validate_evidence_item_queue_review_store_document(tampered)
        except ValueError as exc:
            assert "file_move_performed" in str(exc)
        else:
            raise AssertionError("unsafe file-move flag should fail validation")

        tampered_hash = dict(loaded)
        tampered_hash["queue_review_summary"] = dict(tampered_hash["queue_review_summary"])
        tampered_hash["queue_review_summary"]["queue_item_count"] = 99
        try:
            validate_evidence_item_queue_review_store_document(tampered_hash)
        except ValueError as exc:
            assert "hash mismatch" in str(exc)
        else:
            raise AssertionError("tampered store hash should fail validation")


if __name__ == "__main__":
    run_self_test()
    print("Evidence Item Queue review store self-test passed.")
