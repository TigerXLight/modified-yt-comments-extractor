import json
from dataclasses import dataclass
from enum import Enum

from capture_execution_gate import build_execution_gate_plan, build_execution_gate_request
from evidence_item_queue import EvidenceItemQueue, EvidenceItemRole, EvidenceItemStatus, EvidenceQueueItem
from evidence_item_queue_store import build_evidence_item_queue_review_store_document
from source_evidence_review_export import (
    build_source_evidence_review_manifest,
    build_source_evidence_review_manifest_with_workflow_state,
    source_evidence_review_manifest_to_json,
)
from source_adapter_audit_report import build_source_adapter_audit_report
from source_site_method_audit_registry import build_source_site_method_audit_registry
from source_reference_intake import build_reference_pack_intake_summary
from online_asr_execution_gate import build_online_asr_execution_gate_plan
from total_export_manifest import ASSET_MANIFEST, ASSET_RAW_SIDECAR


class FakeCredentialState(Enum):
    CONFIGURED = "CONFIGURED"


@dataclass(frozen=True)
class FakeCredentialStatus:
    state: FakeCredentialState


@dataclass(frozen=True)
class FakeOnlineASRProvider:
    provider_id: str
    display_name: str
    model_id: str
    credential_entry_id: str


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
    online_asr_provider = FakeOnlineASRProvider(
        provider_id="elevenlabs_scribe",
        display_name="ElevenLabs Scribe v2",
        model_id="scribe_v2",
        credential_entry_id="asr:elevenlabs_scribe",
    )
    _online_asr_plan, online_asr_summary = build_online_asr_execution_gate_plan(
        selected_provider=online_asr_provider,
        provider_options=(online_asr_provider,),
        credential_statuses={
            online_asr_provider.credential_entry_id: FakeCredentialStatus(
                FakeCredentialState.CONFIGURED
            )
        },
        media_file_selected=True,
        media_file_name="clip.mp4",
    )

    manifest = build_source_evidence_review_manifest(
        package_id="source-evidence-review",
        created_at_utc="2026-08-06T12:00:00Z",
        source_urls=("https://example.test/source",),
        queue=queue,
        execution_gate_plan=gate_plan,
        reference_summary=reference_summary,
        queue_review_store_document=store_document,
        online_asr_gate_summary=online_asr_summary,
        app_version="test",
    )
    manifest_dict = manifest.to_dict()
    encoded = source_evidence_review_manifest_to_json(manifest)

    assert manifest_dict["package_id"] == "source-evidence-review"
    assert manifest_dict["capture_options"] == [
        "Evidence Item Queue review metadata",
        "Evidence Item Queue review store metadata",
        "Execution gate approval metadata",
        "Online ASR execution gate metadata",
        "Source reference intake metadata",
    ]
    assert [asset["asset_type"] for asset in manifest_dict["assets"]] == [
        ASSET_MANIFEST,
        ASSET_RAW_SIDECAR,
        ASSET_RAW_SIDECAR,
        ASSET_RAW_SIDECAR,
        ASSET_MANIFEST,
        ASSET_RAW_SIDECAR,
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
    assert "Online ASR provider-call execution gate metadata" in encoded
    assert "provider_call_allowed_without_user_approval" in encoded
    assert json.loads(encoded) == manifest_dict

    repeated = build_source_evidence_review_manifest(
        package_id="source-evidence-review",
        created_at_utc="2026-08-06T12:00:00Z",
        source_urls=("https://example.test/source",),
        queue=queue,
        execution_gate_plan=gate_plan,
        reference_summary=reference_summary,
        queue_review_store_document=store_document,
        online_asr_gate_summary=online_asr_summary,
        app_version="test",
    )
    assert repeated.to_dict() == manifest_dict

    site_method_registry = build_source_site_method_audit_registry()
    audit_report = build_source_adapter_audit_report(site_method_registry=site_method_registry)
    workflow_manifest = build_source_evidence_review_manifest_with_workflow_state(
        manifest,
        workflow_state_metadata={"workflow": "metadata_only"},
        source_site_method_audit_registry_metadata=site_method_registry.to_dict(),
        source_adapter_audit_report_metadata=audit_report.to_dict(),
    )
    workflow_dict = workflow_manifest.to_dict()
    assert "Source site/method audit registry metadata" in workflow_dict["capture_options"]
    assert "Source Adapter audit report metadata" in workflow_dict["capture_options"]
    assert any(
        "Source site/method audit registry metadata sidecar" in asset["description"]
        for asset in workflow_dict["assets"]
    )
    assert any(
        "Source Adapter audit report metadata sidecar" in asset["description"]
        for asset in workflow_dict["assets"]
    )
    assert "Source site/method audit registry metadata sidecar included." in workflow_dict["notes"]
    assert "Source Adapter audit report metadata sidecar included." in workflow_dict["notes"]
    assert all(asset["path"] == "" for asset in workflow_dict["assets"])


if __name__ == "__main__":
    run_self_test()
    print("Source evidence review export self-test passed.")
