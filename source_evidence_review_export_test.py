import json

from capture_execution_gate import build_execution_gate_plan, build_execution_gate_request
from evidence_item_queue import EvidenceItemQueue, EvidenceItemRole, EvidenceItemStatus, EvidenceQueueItem
from evidence_item_queue_store import build_evidence_item_queue_review_store_document
from source_evidence_review_export import (
    build_source_evidence_review_manifest,
    source_evidence_review_manifest_to_json,
)
from source_reference_intake import build_reference_pack_intake_summary
from total_export_manifest import ASSET_MANIFEST, ASSET_RAW_SIDECAR


def run_self_test() -> None:
    queue = EvidenceItemQueue(
        items=(
            EvidenceQueueItem(
                item_id="source_url_1",
                item_role=EvidenceItemRole.SOURCE_URL,
                display_name="example source",
                source_url="https://example.test/source",
                item_status=EvidenceItemStatus.NEEDS_REVIEW,
                created_at_utc="2026-08-06T12:00:00Z",
                updated_at_utc="2026-08-06T12:00:00Z",
            ),
            EvidenceQueueItem(
                item_id="local_media_1",
                item_role=EvidenceItemRole.LOCAL_MEDIA,
                display_name="clip.mp4",
                local_path=r"C:\Users\fahad\Private\clip.mp4",
                file_hash="b" * 64,
                total_export_include=True,
                item_status=EvidenceItemStatus.NEEDS_REVIEW,
                created_at_utc="2026-08-06T12:00:00Z",
                updated_at_utc="2026-08-06T12:00:00Z",
            ),
        )
    )
    gate_request = build_execution_gate_request(
        action_kind="ARCHIVE_CHECK",
        source_label="Example",
        source_url="https://example.test/source",
    )
    gate_plan = build_execution_gate_plan((gate_request,))
    reference_summary = build_reference_pack_intake_summary(records=())
    store_document = build_evidence_item_queue_review_store_document(
        queue,
        session_id="source-review-store",
        timestamp_utc="2026-08-06T12:00:00Z",
        app_version="test",
    )

    manifest = build_source_evidence_review_manifest(
        package_id="source-evidence-review",
        created_at_utc="2026-08-06T12:00:00Z",
        source_urls=("https://example.test/source",),
        queue=queue,
        execution_gate_plan=gate_plan,
        reference_summary=reference_summary,
        queue_review_store_document=store_document,
        app_version="test",
    )
    manifest_dict = manifest.to_dict()
    encoded = source_evidence_review_manifest_to_json(manifest)

    assert manifest_dict["package_id"] == "source-evidence-review"
    assert manifest_dict["capture_options"] == [
        "Evidence Item Queue review metadata",
        "Evidence Item Queue review store metadata",
        "Execution gate approval metadata",
        "Source reference intake metadata",
    ]
    assert [asset["asset_type"] for asset in manifest_dict["assets"]] == [
        ASSET_MANIFEST,
        ASSET_RAW_SIDECAR,
        ASSET_RAW_SIDECAR,
        ASSET_RAW_SIDECAR,
        ASSET_MANIFEST,
    ]
    assert all(asset["path"] == "" for asset in manifest_dict["assets"])
    assert all(len(asset["sha256"]) == 64 for asset in manifest_dict["assets"])
    assert manifest_dict["archive_results"][0]["archive_status"] == "APPROVAL_REQUIRED"
    assert manifest_dict["archive_results"][0]["provider_call_performed"] is False
    assert manifest_dict["archive_results"][0]["submission_performed"] is False
    assert "USER_REVIEW_REQUIRED" in manifest_dict["notes"]
    assert "APPROVAL_REQUIRED" in manifest_dict["notes"]
    assert r"C:\Users\fahad" not in encoded
    assert "clip.mp4" not in encoded
    assert "completed_evidence_claimed" not in encoded
    assert json.loads(encoded) == manifest_dict

    repeated = build_source_evidence_review_manifest(
        package_id="source-evidence-review",
        created_at_utc="2026-08-06T12:00:00Z",
        source_urls=("https://example.test/source",),
        queue=queue,
        execution_gate_plan=gate_plan,
        reference_summary=reference_summary,
        queue_review_store_document=store_document,
        app_version="test",
    )
    assert repeated.to_dict() == manifest_dict


if __name__ == "__main__":
    run_self_test()
    print("Source evidence review export self-test passed.")
