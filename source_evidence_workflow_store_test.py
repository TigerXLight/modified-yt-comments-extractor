import json
import tempfile
from pathlib import Path

from capture_controller import build_operational_capture_plan
from source_evidence_workflow_state import build_source_evidence_workflow_state
from source_evidence_workflow_store import (
    BUNDLE_INDEX_FILENAME,
    ACCESS_PROVIDER_GATE_FILENAME,
    DATABASE_SCAN_RESULT_FILENAME,
    GRABBED_SOURCE_RECORD_FILENAME,
    QUEUE_REVIEW_STORE_FILENAME,
    RELEASE_ACTION_PLAN_FILENAME,
    RELEASE_READINESS_FILENAME,
    REVIEW_MANIFEST_FILENAME,
    SOURCE_ADAPTER_AUDIT_REGISTRY_FILENAME,
    SOURCE_ADAPTER_AUDIT_REPORT_FILENAME,
    SOURCE_SITE_METHOD_AUDIT_REGISTRY_FILENAME,
    WORKFLOW_STATE_FILENAME,
    read_source_evidence_workflow_review_bundle,
    source_evidence_workflow_store_result_to_json,
    validate_source_evidence_workflow_store_result,
    write_source_evidence_workflow_review_bundle,
)
from source_resource_state import build_discussion_capture_options, build_source_resource_row


MSN_URL = "https://www.msn.com/en-gb/news/world/special-dj-by-taku-inoue/ar-AA123456"


def _state():
    row = build_source_resource_row(MSN_URL)
    discussion = build_discussion_capture_options(
        (row,),
        selected_row_id=row.row_id,
        webpage_selected=True,
        webpage_screenshot_requested=True,
        comments_selected=True,
        comments_screenshot_requested=True,
        livechat_selected=False,
        livechat_screenshot_requested=False,
    )
    plan = build_operational_capture_plan(row=row, discussion=discussion)
    return build_source_evidence_workflow_state(
        plan,
        package_id="source review",
        created_at_utc="2026-08-06T12:00:00Z",
        app_version="test-app",
    )


def test_workflow_review_bundle_writes_and_loads_metadata_sidecars_only() -> None:
    state = _state()
    with tempfile.TemporaryDirectory() as temp_dir:
        result = write_source_evidence_workflow_review_bundle(state, temp_dir)
        result_dict = result.to_dict()
        rendered_result = source_evidence_workflow_store_result_to_json(result)

        expected_sidecars = {
            WORKFLOW_STATE_FILENAME,
            REVIEW_MANIFEST_FILENAME,
            QUEUE_REVIEW_STORE_FILENAME,
            RELEASE_READINESS_FILENAME,
            RELEASE_ACTION_PLAN_FILENAME,
            GRABBED_SOURCE_RECORD_FILENAME,
            DATABASE_SCAN_RESULT_FILENAME,
            ACCESS_PROVIDER_GATE_FILENAME,
            SOURCE_ADAPTER_AUDIT_REGISTRY_FILENAME,
            SOURCE_SITE_METHOD_AUDIT_REGISTRY_FILENAME,
            SOURCE_ADAPTER_AUDIT_REPORT_FILENAME,
        }
        expected_files = expected_sidecars | {BUNDLE_INDEX_FILENAME}
        assert {file.filename for file in result.files} == expected_sidecars
        assert result.file_count == 11
        assert result.metadata_file_write_performed is True
        assert result.evidence_file_read_performed is False
        assert result.evidence_file_move_performed is False
        assert result.release_upload_performed is False
        assert result.file_library_publish_performed is False
        assert result.operator_signoff_performed is False
        assert result.completed_release_claimed is False
        assert result.file_existence_claimed is False
        assert result.full_local_path_included is False
        assert result.completed_evidence_claimed is False
        assert result.verified_evidence_claimed is False
        assert len(result_dict["payload_sha256"]) == 64
        validate_source_evidence_workflow_store_result(result_dict)

        for filename in expected_files:
            assert (Path(temp_dir) / filename).is_file()
        assert temp_dir not in rendered_result
        assert "C:\\Users\\fahad" not in rendered_result
        assert "completed evidence" not in rendered_result.lower()
        assert "verified evidence" not in rendered_result.lower()
        assert "final evidence" not in rendered_result.lower()

        loaded = read_source_evidence_workflow_review_bundle(temp_dir)
        loaded_dict = loaded.to_dict()
        assert loaded.bundle["bundle_id"] == result.bundle_id
        assert loaded.workflow_state["review_status"] == "USER_REVIEW_REQUIRED"
        assert loaded.review_manifest["assets"]
        assert loaded.queue_review_store["metadata_only"] is True
        assert loaded.release_readiness["release_status"] == "RELEASE_APPROVAL_REQUIRED"
        assert loaded.release_readiness["target_count"] == 4
        assert loaded.release_action_plan["release_status"] == "RELEASE_APPROVAL_REQUIRED"
        assert loaded.release_action_plan["operator_signoff_required"] is True
        assert loaded.release_action_plan["receipt_count"] == 4
        assert loaded.release_action_plan["command_count"] == 0
        assert loaded.grabbed_source_record["review_state"] == "USER_REVIEW_REQUIRED"
        assert loaded.grabbed_source_record["metadata_only"] is True
        assert loaded.grabbed_source_record["artifact_count"] > 0
        assert loaded.database_scan_result["matched_record_count"] >= 1
        assert loaded.database_scan_result["file_read_performed"] is False
        assert loaded.database_scan_result["broad_scan_performed"] is False
        assert loaded.access_provider_gate_summary["review_status"] == "USER_REVIEW_REQUIRED"
        assert loaded.access_provider_gate_summary["credential_lookup_performed"] is False
        assert loaded.access_provider_gate_summary["provider_call_performed"] is False
        assert loaded.access_provider_gate_summary["record_count"] > 0
        assert loaded.source_adapter_audit_registry["review_status"] == "USER_REVIEW_REQUIRED"
        assert loaded.source_adapter_audit_registry["entry_count"] == 9
        assert loaded.source_adapter_audit_registry["audit_required_count"] == 0
        assert loaded.source_adapter_audit_registry["not_yet_executed_count"] == 9
        assert loaded.source_adapter_audit_registry["live_execution_performed"] is False
        assert loaded.source_adapter_audit_registry["browser_automation_performed"] is False
        assert loaded.source_site_method_audit_registry["review_status"] == "USER_REVIEW_REQUIRED"
        assert loaded.source_site_method_audit_registry["row_count"] == 11
        assert loaded.source_site_method_audit_registry["selector_audit_required_count"] == 1
        assert loaded.source_site_method_audit_registry["live_approved_only_count"] == 1
        assert loaded.source_site_method_audit_registry["live_execution_performed"] is False
        assert loaded.source_site_method_audit_registry["browser_automation_performed"] is False
        assert loaded.source_adapter_audit_report["review_status"] == "USER_REVIEW_REQUIRED"
        assert loaded.source_adapter_audit_report["row_count"] == 20
        assert loaded.source_adapter_audit_report["selector_audit_required_count"] == 1
        assert loaded.source_adapter_audit_report["live_execution_performed"] is False
        assert {
            target["target_kind"] for target in loaded.release_readiness["targets"]
        } == {
            "total_export_release_manifest",
            "release_upload_target_receipt",
            "file_library_publish_receipt",
            "operator_signoff_receipt",
        }
        assert loaded.metadata_file_read_performed is True
        assert loaded.evidence_file_read_performed is False
        assert loaded.evidence_file_move_performed is False
        assert loaded.file_existence_claimed is False
        assert loaded.full_local_path_included is False
        encoded = json.dumps(loaded_dict, sort_keys=True)
        assert temp_dir not in encoded
        assert "C:\\Users\\fahad" not in encoded


def test_review_manifest_gets_workflow_state_metadata_sidecar() -> None:
    state = _state()
    with tempfile.TemporaryDirectory() as temp_dir:
        write_source_evidence_workflow_review_bundle(state, temp_dir)
        manifest = json.loads((Path(temp_dir) / REVIEW_MANIFEST_FILENAME).read_text(encoding="utf-8"))

    assert "Source Evidence workflow state metadata" in manifest["capture_options"]
    assert "Source Evidence release readiness metadata" in manifest["capture_options"]
    assert "Source Adapter audit registry metadata" in manifest["capture_options"]
    assert "Source site/method audit registry metadata" in manifest["capture_options"]
    assert "Source Adapter audit report metadata" in manifest["capture_options"]
    assert any(
        asset["description"] == "Source Evidence workflow state metadata bundle sidecar."
        for asset in manifest["assets"]
    )
    assert any(
        "Source Adapter audit registry metadata sidecar" in asset["description"]
        for asset in manifest["assets"]
    )
    assert any(
        "Source site/method audit registry metadata sidecar" in asset["description"]
        for asset in manifest["assets"]
    )
    assert any(
        "Source Adapter audit report metadata sidecar" in asset["description"]
        for asset in manifest["assets"]
    )
    assert any(
        "Source Evidence release readiness metadata" in asset["description"]
        for asset in manifest["assets"]
    )
    assert all(asset["path"] == "" for asset in manifest["assets"])
    assert "Source Evidence workflow state metadata sidecar included." in manifest["notes"]
    assert "Source Evidence release readiness metadata sidecar included." in manifest["notes"]
    assert "Source Adapter audit registry metadata sidecar included." in manifest["notes"]
    assert "Source site/method audit registry metadata sidecar included." in manifest["notes"]
    assert "Source Adapter audit report metadata sidecar included." in manifest["notes"]


def test_workflow_review_bundle_hash_validation_rejects_tampering() -> None:
    state = _state()
    with tempfile.TemporaryDirectory() as temp_dir:
        write_source_evidence_workflow_review_bundle(state, temp_dir)
        index_path = Path(temp_dir) / BUNDLE_INDEX_FILENAME
        document = json.loads(index_path.read_text(encoding="utf-8"))
        document["files"][0]["filename"] = "tampered.json"
        index_path.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
        try:
            read_source_evidence_workflow_review_bundle(temp_dir)
        except ValueError as error:
            assert "hash mismatch" in str(error)
        else:
            raise AssertionError("Tampered workflow store bundle should fail validation")


def run_self_test() -> None:
    test_workflow_review_bundle_writes_and_loads_metadata_sidecars_only()
    test_review_manifest_gets_workflow_state_metadata_sidecar()
    test_workflow_review_bundle_hash_validation_rejects_tampering()


if __name__ == "__main__":
    run_self_test()
    print("Source evidence workflow store self-test passed.")
