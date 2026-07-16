from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from capture_contracts import (
    ARTIFACT_TYPE_ACCESSIBILITY_TREE,
    ARTIFACT_TYPE_ACTION_LOG,
    ARTIFACT_TYPE_ARCHIVE_RESULT,
    ARTIFACT_TYPE_ARTICLE_TEXT,
    ARTIFACT_TYPE_COMMENTS_JSONL,
    ARTIFACT_TYPE_COMMENTS_TEXT,
    ARTIFACT_TYPE_DOM_SNAPSHOT,
    ARTIFACT_TYPE_FINAL_DOM,
    ARTIFACT_TYPE_LIVECHAT_JSONL,
    ARTIFACT_TYPE_LIVECHAT_TEXT,
    ARTIFACT_TYPE_MEDIA_COMPONENT,
    ARTIFACT_TYPE_MEDIA_FILE,
    ARTIFACT_TYPE_MEDIA_INVENTORY,
    ARTIFACT_TYPE_MHTML,
    ARTIFACT_TYPE_PAGE_OUTLINE,
    ARTIFACT_TYPE_RAW_HTML,
    ARTIFACT_TYPE_RENDERED_RECORDING,
    ARTIFACT_TYPE_SCREENSHOT,
    ARTIFACT_TYPE_WACZ,
    ARTIFACT_TYPE_WARC,
    CaptureArtifact,
)
from capture_controller import OperationalCapturePlanResult
from evidence_database_index import (
    EvidenceClassificationValue,
    EvidenceIndexRecord,
    build_classification_state,
    build_evidence_basis,
    build_evidence_item_identity,
    stable_evidence_id,
)
from evidence_database_review import (
    EvidenceDatabasePreviewRequest,
    EvidenceDatabasePreviewResult,
    build_preview_result_from_records,
    build_review_session,
)
from evidence_item_queue import (
    EvidenceItemLink,
    EvidenceItemQueue,
    EvidenceItemRole,
    EvidenceItemStatus,
    EvidenceLinkOrigin,
    EvidenceQueueItem,
)
from total_export_manifest import (
    ASSET_ARCHIVE_RESULT,
    ASSET_EXTRACTED_TEXT,
    ASSET_HTML_SNAPSHOT,
    ASSET_MEDIA,
    ASSET_RAW_SIDECAR,
    ASSET_SCREENSHOT,
    ExportAsset,
    TotalExportManifest,
    safe_package_id,
)


CAPTURE_EXPORT_QUEUE_SCOPE = (
    "operational capture export/queue metadata only; no file writes, no file moves, "
    "no broad folder scans, no live capture, no screenshots, no downloads, no archive "
    "provider calls, no WARC capture, no WACZ packaging, no ArchiveBox execution, "
    "no provider/network behavior, no credential access, and no automatic classification"
)

PLAN_STATUS_NON_EXECUTING = "non_executing_plan"
PLAN_STATUS_USER_REVIEW_REQUIRED = "user_review_required"

_TEXT_ARTIFACT_TYPES = {
    ARTIFACT_TYPE_ARTICLE_TEXT,
    ARTIFACT_TYPE_PAGE_OUTLINE,
    ARTIFACT_TYPE_COMMENTS_JSONL,
    ARTIFACT_TYPE_COMMENTS_TEXT,
    ARTIFACT_TYPE_LIVECHAT_JSONL,
    ARTIFACT_TYPE_LIVECHAT_TEXT,
}

_HTML_ARTIFACT_TYPES = {
    ARTIFACT_TYPE_RAW_HTML,
    ARTIFACT_TYPE_FINAL_DOM,
    ARTIFACT_TYPE_MHTML,
    ARTIFACT_TYPE_DOM_SNAPSHOT,
    ARTIFACT_TYPE_ACCESSIBILITY_TREE,
}

_MEDIA_ARTIFACT_TYPES = {
    ARTIFACT_TYPE_MEDIA_INVENTORY,
    ARTIFACT_TYPE_MEDIA_FILE,
    ARTIFACT_TYPE_MEDIA_COMPONENT,
    ARTIFACT_TYPE_RENDERED_RECORDING,
}


@dataclass(frozen=True)
class OperationalCaptureExportQueueConnection:
    queue: EvidenceItemQueue
    total_export_manifest: TotalExportManifest
    evidence_index_records: tuple[EvidenceIndexRecord, ...]
    review_preview: EvidenceDatabasePreviewResult
    scope: str = CAPTURE_EXPORT_QUEUE_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_index_records": [
                record.to_dict() for record in self.evidence_index_records
            ],
            "queue": self.queue.to_dict(),
            "review_preview": self.review_preview.to_dict(),
            "scope": self.scope,
            "total_export_manifest": self.total_export_manifest.to_dict(),
        }


def _stable_note(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _artifact_display_name(artifact: CaptureArtifact) -> str:
    return f"Planned {artifact.artifact_type}: {artifact.relative_path}"


def _queue_role_for_artifact(artifact_type: str) -> EvidenceItemRole:
    if artifact_type == ARTIFACT_TYPE_SCREENSHOT:
        return EvidenceItemRole.SCREENSHOT
    if artifact_type in _HTML_ARTIFACT_TYPES:
        return EvidenceItemRole.HTML_SNAPSHOT
    if artifact_type in _TEXT_ARTIFACT_TYPES:
        return EvidenceItemRole.VISIBLE_TEXT_SNAPSHOT
    if artifact_type == ARTIFACT_TYPE_ARCHIVE_RESULT:
        return EvidenceItemRole.ARCHIVE_URL
    if artifact_type in _MEDIA_ARTIFACT_TYPES:
        return EvidenceItemRole.LOCAL_MEDIA
    return EvidenceItemRole.MANUAL_EVIDENCE_NOTE


def _manifest_asset_type_for_artifact(artifact_type: str) -> str:
    if artifact_type == ARTIFACT_TYPE_SCREENSHOT:
        return ASSET_SCREENSHOT
    if artifact_type in _HTML_ARTIFACT_TYPES:
        return ASSET_HTML_SNAPSHOT
    if artifact_type in _TEXT_ARTIFACT_TYPES:
        return ASSET_EXTRACTED_TEXT
    if artifact_type == ARTIFACT_TYPE_ARCHIVE_RESULT:
        return ASSET_ARCHIVE_RESULT
    if artifact_type in _MEDIA_ARTIFACT_TYPES:
        return ASSET_MEDIA
    return ASSET_RAW_SIDECAR


def _artifact_metadata_note(
    artifact: CaptureArtifact,
    *,
    plan: OperationalCapturePlanResult,
) -> str:
    return _stable_note(
        {
            "action_log_artifact_id": (
                plan.action_log_artifact.artifact_id
                if plan.action_log_artifact is not None
                else ""
            ),
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "capture_method": artifact.capture_method,
            "execution": "not executed",
            "fixture_or_mock_metadata": True,
            "manual_live_site_smoke_pending": True,
            "operational_status": plan.operational_status,
            "queue_metadata_only": True,
            "relative_path": artifact.relative_path,
            "scope": artifact.scope,
            "sha256": artifact.sha256,
            "source_row_id": plan.source_row_id,
            "total_export_metadata_only": True,
            "user_review_required": True,
        }
    )


def _all_plan_artifacts(plan: OperationalCapturePlanResult) -> tuple[CaptureArtifact, ...]:
    if plan.action_log_artifact is None:
        return plan.declared_artifacts
    return plan.declared_artifacts + (plan.action_log_artifact,)


def operational_capture_plan_to_evidence_queue(
    plan: OperationalCapturePlanResult,
) -> EvidenceItemQueue:
    source_item_id = stable_evidence_id(
        "queue_source",
        plan.source_row_id,
        plan.canonical_url,
    )
    source_item = EvidenceQueueItem(
        item_id=source_item_id,
        item_role=EvidenceItemRole.SOURCE_URL,
        display_name=plan.source_title or plan.canonical_url,
        source_url=plan.canonical_url,
        linked_source_id=plan.source_row_id,
        item_status=EvidenceItemStatus.NEEDS_REVIEW,
        user_notes=_stable_note(
            {
                "adapter_id": plan.adapter_id,
                "execution": "not executed",
                "manual_live_site_smoke_pending": True,
                "selected_modes": plan.selected_modes,
                "source_row_id": plan.source_row_id,
                "user_review_required": True,
            }
        ),
    )
    items: list[EvidenceQueueItem] = [source_item]
    links: list[EvidenceItemLink] = []
    for artifact in _all_plan_artifacts(plan):
        item_id = stable_evidence_id("queue_artifact", artifact.artifact_id)
        items.append(
            EvidenceQueueItem(
                item_id=item_id,
                item_role=_queue_role_for_artifact(artifact.artifact_type),
                display_name=_artifact_display_name(artifact),
                source_url=plan.canonical_url,
                linked_source_id=plan.source_row_id,
                file_hash=artifact.sha256,
                total_export_include=True,
                total_export_output_kind=_manifest_asset_type_for_artifact(
                    artifact.artifact_type
                ),
                total_export_output_path=artifact.relative_path,
                item_status=EvidenceItemStatus.NEEDS_REVIEW,
                user_notes=_artifact_metadata_note(artifact, plan=plan),
            )
        )
        links.append(
            EvidenceItemLink(
                source_item_id=source_item_id,
                target_item_id=item_id,
                relationship="planned_operational_capture_artifact",
                link_origin=EvidenceLinkOrigin.DERIVED_FROM_APP_STATE,
                notes="Metadata-only link from selected source to planned artifact; no file operation performed.",
            )
        )
    return EvidenceItemQueue(items=tuple(items), links=tuple(links))


def operational_capture_plan_to_total_export_manifest(
    plan: OperationalCapturePlanResult,
    *,
    package_id: str = "",
    output_folder: str = "",
) -> TotalExportManifest:
    safe_id = safe_package_id(package_id or f"operational_capture_{plan.source_row_id}")
    assets: list[ExportAsset] = []
    archive_results: list[dict[str, Any]] = []
    for artifact in _all_plan_artifacts(plan):
        description = _artifact_metadata_note(artifact, plan=plan)
        assets.append(
            ExportAsset(
                asset_type=_manifest_asset_type_for_artifact(artifact.artifact_type),
                path=artifact.relative_path,
                description=description,
                source_url=plan.canonical_url,
                created_at_utc=artifact.created_at_utc,
                sha256=artifact.sha256,
                size_bytes=artifact.size_bytes,
            )
        )
        archive_results.append(
            {
                "action_log_artifact_id": (
                    plan.action_log_artifact.artifact_id
                    if plan.action_log_artifact is not None
                    else ""
                ),
                "artifact_id": artifact.artifact_id,
                "artifact_type": artifact.artifact_type,
                "capture_method": artifact.capture_method,
                "execution": "not executed",
                "manual_live_site_smoke_pending": True,
                "non_executing_status": PLAN_STATUS_NON_EXECUTING,
                "relative_path": artifact.relative_path,
                "scope": artifact.scope,
                "sha256": artifact.sha256,
                "user_review_required": True,
            }
        )
    return TotalExportManifest(
        package_id=safe_id,
        source_urls=[plan.canonical_url],
        output_folder=output_folder,
        capture_options=list(plan.selected_modes)
        + [f"screenshot:{item}" for item in plan.screenshot_intents],
        assets=assets,
        archive_results=archive_results,
        notes=_stable_note(
            {
                "export_metadata_only": True,
                "manual_live_site_smoke_pending": True,
                "non_executing_status": PLAN_STATUS_NON_EXECUTING,
                "source_row_id": plan.source_row_id,
                "user_review_required": True,
            }
        ),
    )


def operational_capture_plan_to_evidence_index_records(
    plan: OperationalCapturePlanResult,
    *,
    database_root_id: str = "",
    taxonomy_version_id: str = "",
) -> tuple[EvidenceIndexRecord, ...]:
    records: list[EvidenceIndexRecord] = []
    for artifact in _all_plan_artifacts(plan):
        item_id = stable_evidence_id("edi_capture_artifact", artifact.artifact_id)
        identity = build_evidence_item_identity(
            display_name=_artifact_display_name(artifact),
            source_url=plan.canonical_url,
            queue_item_id=stable_evidence_id("queue_artifact", artifact.artifact_id),
            source_row_id=plan.source_row_id,
            item_id=item_id,
        )
        basis = build_evidence_basis(
            item_id=identity.item_id,
            basis_type="operational_capture_plan_artifact",
            source_url=plan.canonical_url,
            evidence_text=(
                f"{artifact.artifact_type} planned as {artifact.relative_path}; "
                "not executed and requires user review."
            ),
            user_note=_artifact_metadata_note(artifact, plan=plan),
            confidence="model_only_fixture_or_mock_metadata",
        )
        classification = build_classification_state(
            classification_value=EvidenceClassificationValue.UNKNOWN,
            dimensions={
                "artifact_type": artifact.artifact_type,
                "capture_method": artifact.capture_method,
                "execution": "not_executed",
                "manual_live_site_smoke": "pending",
                "source_adapter": plan.adapter_id,
            },
            source_evidenced=False,
            user_confirmed=False,
            notes=(
                "Operational capture artifact metadata only; USER_REVIEW_REQUIRED; "
                "no scanning, file movement, or automatic classification."
            ),
        )
        records.append(
            EvidenceIndexRecord(
                identity=identity,
                database_root_id=database_root_id,
                taxonomy_version_id=taxonomy_version_id,
                classification_state=classification,
                evidence_basis=(basis,),
            )
        )
    return tuple(records)


def operational_capture_plan_to_review_preview(
    plan: OperationalCapturePlanResult,
    *,
    database_root_id: str = "",
    taxonomy_version_id: str = "",
) -> EvidenceDatabasePreviewResult:
    records = operational_capture_plan_to_evidence_index_records(
        plan,
        database_root_id=database_root_id,
        taxonomy_version_id=taxonomy_version_id,
    )
    session = build_review_session(
        selected_root_id=database_root_id,
        taxonomy_version_id=taxonomy_version_id,
        registered_root_ids=(database_root_id,) if database_root_id else (),
    )
    request = EvidenceDatabasePreviewRequest(
        session_id=session.session_id,
        root_id=database_root_id,
        record_ids=tuple(record.identity.item_id for record in records),
    )
    return build_preview_result_from_records(
        request,
        records,
        warnings=(
            "USER_REVIEW_REQUIRED",
            "MANUAL_LIVE_SITE_SMOKE_PENDING",
            "DESTRUCTIVE_ACTION_NOT_IMPLEMENTED",
        ),
    )


def connect_operational_capture_plan_to_export_queue(
    plan: OperationalCapturePlanResult,
    *,
    package_id: str = "",
    output_folder: str = "",
    database_root_id: str = "",
    taxonomy_version_id: str = "",
) -> OperationalCaptureExportQueueConnection:
    records = operational_capture_plan_to_evidence_index_records(
        plan,
        database_root_id=database_root_id,
        taxonomy_version_id=taxonomy_version_id,
    )
    preview = operational_capture_plan_to_review_preview(
        plan,
        database_root_id=database_root_id,
        taxonomy_version_id=taxonomy_version_id,
    )
    return OperationalCaptureExportQueueConnection(
        queue=operational_capture_plan_to_evidence_queue(plan),
        total_export_manifest=operational_capture_plan_to_total_export_manifest(
            plan,
            package_id=package_id,
            output_folder=output_folder,
        ),
        evidence_index_records=records,
        review_preview=preview,
    )
