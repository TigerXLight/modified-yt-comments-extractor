from capture_controller import build_operational_capture_plan
from capture_contracts import (
    ARTIFACT_TYPE_ACTION_LOG,
    ARTIFACT_TYPE_COMMENTS_JSONL,
    ARTIFACT_TYPE_RAW_HTML,
    ZERO_SHA256,
)
from capture_export_queue import (
    PLAN_STATUS_NON_EXECUTING,
    connect_operational_capture_plan_to_export_queue,
    operational_capture_plan_to_evidence_index_records,
    operational_capture_plan_to_evidence_queue,
    operational_capture_plan_to_total_export_manifest,
)
from evidence_database_index import EvidenceClassificationValue
from evidence_item_queue import EvidenceItemRole, EvidenceItemStatus
from source_resource_state import build_discussion_capture_options, build_source_resource_row
from total_export_manifest import ASSET_EXTRACTED_TEXT, ASSET_HTML_SNAPSHOT, ASSET_RAW_SIDECAR


MSN_URL = "https://www.msn.com/en-gb/news/world/special-dj-by-taku-inoue/ar-AA123456"


def _plan():
    row = build_source_resource_row(MSN_URL)
    discussion = build_discussion_capture_options(
        (row,),
        selected_row_id=row.row_id,
        webpage_selected=True,
        webpage_screenshot_requested=False,
        comments_selected=True,
        comments_screenshot_requested=False,
        livechat_selected=False,
        livechat_screenshot_requested=False,
    )
    return build_operational_capture_plan(row=row, discussion=discussion)


def test_operational_capture_plan_converts_to_evidence_queue_without_file_claims() -> None:
    plan = _plan()
    queue = operational_capture_plan_to_evidence_queue(plan)
    queue_dict = queue.to_dict()

    assert len(queue.items) == len(plan.declared_artifacts) + 2  # source row + artifacts + action log
    assert queue.items[0].item_role is EvidenceItemRole.SOURCE_URL
    assert queue.items[0].source_url == plan.canonical_url
    assert queue.items[0].item_status is EvidenceItemStatus.NEEDS_REVIEW
    assert len(queue.links) == len(plan.declared_artifacts) + 1
    assert all(item.local_path == "" for item in queue.items)
    assert all(item.item_status is EvidenceItemStatus.NEEDS_REVIEW for item in queue.items)

    artifact_items = queue.items[1:]
    first_note = artifact_items[0].user_notes
    assert plan.declared_artifacts[0].artifact_id in first_note
    assert "not executed" in first_note
    assert "manual_live_site_smoke_pending" in first_note
    assert artifact_items[0].file_hash == ZERO_SHA256
    assert artifact_items[0].total_export_include is True
    assert artifact_items[0].total_export_output_path == "page/raw.html"
    assert any(item.item_role is EvidenceItemRole.VISIBLE_TEXT_SNAPSHOT for item in artifact_items)
    assert any(
        item.item_role is EvidenceItemRole.MANUAL_EVIDENCE_NOTE
        and item.total_export_output_kind == ASSET_RAW_SIDECAR
        for item in artifact_items
    )
    rendered = repr(queue_dict)
    assert "api_key" not in rendered
    assert "Cookie" not in rendered
    assert "Authorization" not in rendered


def test_operational_capture_plan_converts_to_total_export_manifest_metadata_only() -> None:
    plan = _plan()
    manifest = operational_capture_plan_to_total_export_manifest(
        plan,
        package_id="Source Plan!",
        output_folder="",
    )
    manifest_dict = manifest.to_dict()

    assert manifest.package_id == "Source_Plan"
    assert manifest.source_urls == [plan.canonical_url]
    assert "webpage" in manifest.capture_options
    assert "comments" in manifest.capture_options
    assert len(manifest.assets) == len(plan.declared_artifacts) + 1
    assert len(manifest.archive_results) == len(manifest.assets)
    assert manifest.assets[0].asset_type == ASSET_HTML_SNAPSHOT
    assert manifest.assets[0].path == "page/raw.html"
    assert plan.declared_artifacts[0].artifact_id in manifest.assets[0].description
    assert any(asset.asset_type == ASSET_EXTRACTED_TEXT for asset in manifest.assets)
    assert manifest.assets[-1].asset_type == ASSET_RAW_SIDECAR
    assert manifest.archive_results[-1]["artifact_type"] == ARTIFACT_TYPE_ACTION_LOG
    assert manifest.archive_results[-1]["non_executing_status"] == PLAN_STATUS_NON_EXECUTING
    assert manifest.archive_results[-1]["manual_live_site_smoke_pending"] is True
    assert "export_metadata_only" in manifest.notes
    assert "not executed" in repr(manifest_dict)
    assert "LIVE_SITE_MANUALLY_VERIFIED" not in repr(manifest_dict)


def test_operational_capture_plan_converts_to_review_records_without_scan_or_classification() -> None:
    plan = _plan()
    records = operational_capture_plan_to_evidence_index_records(
        plan,
        database_root_id="demo-root",
        taxonomy_version_id="taxonomy-v1",
    )

    assert len(records) == len(plan.declared_artifacts) + 1
    first = records[0]
    assert first.identity.source_url == plan.canonical_url
    assert first.database_root_id == "demo-root"
    assert first.taxonomy_version_id == "taxonomy-v1"
    assert first.classification_state.classification_value is EvidenceClassificationValue.UNKNOWN
    assert first.classification_state.user_confirmation_required is True
    assert first.classification_state.source_evidenced is False
    assert first.path_records == ()
    assert first.placement_proposals == ()
    assert first.reclassification_proposals == ()
    assert first.evidence_basis[0].basis_type == "operational_capture_plan_artifact"
    assert "USER_REVIEW_REQUIRED" in first.classification_state.notes
    assert "not executed" in first.evidence_basis[0].evidence_text


def test_connection_result_includes_review_preview_and_preserves_action_log_hashes() -> None:
    plan = _plan()
    connection = connect_operational_capture_plan_to_export_queue(
        plan,
        package_id="review package",
        database_root_id="demo-root",
        taxonomy_version_id="taxonomy-v1",
    )
    data = connection.to_dict()

    assert connection.review_preview.supplied_records_only is True
    assert connection.review_preview.broad_scan_performed is False
    assert connection.review_preview.file_operation_performed is False
    assert connection.review_preview.record_count == len(connection.evidence_index_records)
    assert "USER_REVIEW_REQUIRED" in connection.review_preview.warnings
    assert "MANUAL_LIVE_SITE_SMOKE_PENDING" in connection.review_preview.warnings
    assert connection.queue.items[-1].file_hash == plan.action_log_artifact.sha256
    assert connection.total_export_manifest.assets[-1].sha256 == plan.action_log_artifact.sha256
    assert plan.action_log_artifact.artifact_id in connection.queue.items[-1].user_notes
    assert plan.action_log_artifact.artifact_id in connection.total_export_manifest.assets[-1].description
    assert data["scope"].startswith("operational capture export/queue metadata only")
    assert "file_operation_performed" not in repr(data["queue"])
    assert "not executed" in repr(data)


def test_artifact_types_preserved_in_queue_and_manifest() -> None:
    plan = _plan()
    queue = operational_capture_plan_to_evidence_queue(plan)
    manifest = operational_capture_plan_to_total_export_manifest(plan)
    queue_notes = "\n".join(item.user_notes for item in queue.items)
    manifest_notes = "\n".join(asset.description for asset in manifest.assets)

    for artifact_type in (ARTIFACT_TYPE_RAW_HTML, ARTIFACT_TYPE_COMMENTS_JSONL, ARTIFACT_TYPE_ACTION_LOG):
        assert artifact_type in queue_notes
        assert artifact_type in manifest_notes
    assert "completed_live_capture" not in queue_notes
    assert "completed_live_capture" not in manifest_notes


def run_self_test() -> None:
    test_operational_capture_plan_converts_to_evidence_queue_without_file_claims()
    test_operational_capture_plan_converts_to_total_export_manifest_metadata_only()
    test_operational_capture_plan_converts_to_review_records_without_scan_or_classification()
    test_connection_result_includes_review_preview_and_preserves_action_log_hashes()
    test_artifact_types_preserved_in_queue_and_manifest()


if __name__ == "__main__":
    run_self_test()
    print("Capture export queue self-test passed.")
