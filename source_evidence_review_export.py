from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Mapping

from capture_execution_gate import ExecutionGatePlan
from evidence_item_queue import (
    EvidenceItemQueue,
    build_evidence_item_queue_review_activity_flow_summary,
    build_evidence_item_queue_review_summary,
)
from source_reference_intake import ReferencePackIntakeSummary
from evidence_item_queue_store import EvidenceItemQueueReviewStoreDocument
from total_export_manifest import ASSET_MANIFEST, ASSET_RAW_SIDECAR, ExportAsset, TotalExportManifest


SOURCE_EVIDENCE_REVIEW_EXPORT_SCHEMA_VERSION = "source_evidence_review_export_v1"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _stable_json(data: Any) -> str:
    return json.dumps(_value_for_dict(data), sort_keys=True, separators=(",", ":"))


def _sha256(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()


def _metadata_asset(*, asset_type: str, description: str, metadata: dict[str, Any], created_at_utc: str) -> ExportAsset:
    return ExportAsset(
        asset_type=asset_type,
        description=description,
        created_at_utc=created_at_utc,
        sha256=_sha256(metadata),
        mime_type="application/json",
        size_bytes=len(_stable_json(metadata).encode("utf-8")),
    )


def build_source_evidence_review_manifest(
    *,
    package_id: str,
    created_at_utc: str,
    source_urls: tuple[str, ...] = (),
    queue: EvidenceItemQueue | None = None,
    execution_gate_plan: ExecutionGatePlan | None = None,
    reference_summary: ReferencePackIntakeSummary | None = None,
    queue_review_store_document: EvidenceItemQueueReviewStoreDocument | Mapping[str, Any] | None = None,
    workflow_state_metadata: Mapping[str, Any] | None = None,
    release_readiness_metadata: Mapping[str, Any] | None = None,
    online_asr_gate_summary: Mapping[str, Any] | Any | None = None,
    app_version: str = "",
) -> TotalExportManifest:
    assets: list[ExportAsset] = []
    capture_options: list[str] = []
    archive_results: list[dict[str, Any]] = []

    if queue is not None:
        queue_summary = build_evidence_item_queue_review_summary(queue).to_dict()
        flow_summary = build_evidence_item_queue_review_activity_flow_summary(
            queue,
            session_id=f"{package_id}_queue_review",
            timestamp_utc=created_at_utc,
            app_version=app_version,
        ).to_dict()
        assets.append(
            _metadata_asset(
                asset_type=ASSET_MANIFEST,
                description="Evidence Item Queue review summary metadata (USER_REVIEW_REQUIRED).",
                metadata=queue_summary,
                created_at_utc=created_at_utc,
            )
        )
        assets.append(
            _metadata_asset(
                asset_type=ASSET_RAW_SIDECAR,
                description="Evidence Item Queue action/provenance activity flow metadata.",
                metadata=flow_summary,
                created_at_utc=created_at_utc,
            )
        )
        capture_options.append("Evidence Item Queue review metadata")

    if execution_gate_plan is not None:
        gate_metadata = execution_gate_plan.to_dict()
        assets.append(
            _metadata_asset(
                asset_type=ASSET_RAW_SIDECAR,
                description="Execution gate approval-required metadata.",
                metadata=gate_metadata,
                created_at_utc=created_at_utc,
            )
        )
        capture_options.append("Execution gate approval metadata")
        if any("ARCHIVE" in request.action_kind.value for request in execution_gate_plan.requests):
            archive_results.append(
                {
                    "archive_service": "manual_or_mock_provider_only",
                    "archive_status": execution_gate_plan.status,
                    "execution_state": "EXECUTION_GATED",
                    "provider_call_performed": False,
                    "submission_performed": False,
                    "user_review_required": True,
                }
            )

    if reference_summary is not None:
        reference_metadata = reference_summary.to_dict()
        assets.append(
            _metadata_asset(
                asset_type=ASSET_RAW_SIDECAR,
                description="Source reference intake metadata; reference-only use boundaries.",
                metadata=reference_metadata,
                created_at_utc=created_at_utc,
            )
        )
        capture_options.append("Source reference intake metadata")

    if queue_review_store_document is not None:
        store_metadata = _value_for_dict(queue_review_store_document)
        assets.append(
            _metadata_asset(
                asset_type=ASSET_MANIFEST,
                description="Evidence Item Queue review store document metadata.",
                metadata=store_metadata,
                created_at_utc=created_at_utc,
            )
        )
        capture_options.append("Evidence Item Queue review store metadata")

    if workflow_state_metadata is not None:
        workflow_metadata = _value_for_dict(workflow_state_metadata)
        assets.append(
            _metadata_asset(
                asset_type=ASSET_RAW_SIDECAR,
                description="Source Evidence workflow state metadata bundle sidecar.",
                metadata=workflow_metadata,
                created_at_utc=created_at_utc,
            )
        )
        capture_options.append("Source Evidence workflow state metadata")

    if release_readiness_metadata is not None:
        release_metadata = _value_for_dict(release_readiness_metadata)
        assets.append(
            _metadata_asset(
                asset_type=ASSET_MANIFEST,
                description=(
                    "Source Evidence release readiness metadata: Total Export release, "
                    "release-upload, file-library, and operator-signoff targets remain "
                    "approval-required and not executed."
                ),
                metadata=release_metadata,
                created_at_utc=created_at_utc,
            )
        )
        capture_options.append("Source Evidence release readiness metadata")

    if online_asr_gate_summary is not None:
        online_asr_metadata = _value_for_dict(online_asr_gate_summary)
        assets.append(
            _metadata_asset(
                asset_type=ASSET_RAW_SIDECAR,
                description=(
                    "Online ASR provider-call execution gate metadata; "
                    "provider_call_allowed_without_user_approval=false."
                ),
                metadata=online_asr_metadata,
                created_at_utc=created_at_utc,
            )
        )
        capture_options.append("Online ASR execution gate metadata")

    notes = "\n".join(
        [
            "Source evidence review manifest metadata only.",
            "Status labels: METADATA_ONLY / LOCAL_ONLY / USER_REVIEW_REQUIRED / APPROVAL_REQUIRED.",
            "No raw payloads, full local paths, file-existence claims, completed-evidence claims, live/API/browser/archive/download/OCR/classification execution, or evidence file movement.",
            f"Schema: {SOURCE_EVIDENCE_REVIEW_EXPORT_SCHEMA_VERSION}",
        ]
    )
    return TotalExportManifest(
        package_id=package_id,
        created_at_utc=created_at_utc,
        source_urls=sorted(set(source_urls)),
        capture_options=sorted(capture_options),
        assets=assets,
        archive_results=archive_results,
        notes=notes,
        app_version=app_version,
    )


def build_source_evidence_review_manifest_with_workflow_state(
    manifest: TotalExportManifest,
    *,
    workflow_state_metadata: Mapping[str, Any],
    release_readiness_metadata: Mapping[str, Any] | None = None,
    source_adapter_audit_registry_metadata: Mapping[str, Any] | None = None,
    source_site_method_audit_registry_metadata: Mapping[str, Any] | None = None,
) -> TotalExportManifest:
    """Return a manifest copy with a workflow-state metadata sidecar asset.

    The added asset is metadata-only and pathless. It lets Total Export carry the
    app-facing execution-gated workflow state without writing or claiming evidence
    artifact files.
    """
    metadata = _value_for_dict(workflow_state_metadata)
    workflow_asset = _metadata_asset(
        asset_type=ASSET_RAW_SIDECAR,
        description="Source Evidence workflow state metadata bundle sidecar.",
        metadata=metadata,
        created_at_utc=manifest.created_at_utc,
    )
    assets = list(manifest.assets) + [workflow_asset]
    capture_option_values = set(list(manifest.capture_options) + ["Source Evidence workflow state metadata"])
    if release_readiness_metadata is not None:
        release_metadata = _value_for_dict(release_readiness_metadata)
        assets.append(
            _metadata_asset(
                asset_type=ASSET_MANIFEST,
                description=(
                    "Source Evidence release readiness metadata: Total Export release, "
                    "release-upload, file-library, and operator-signoff targets remain "
                    "approval-required and not executed."
                ),
                metadata=release_metadata,
                created_at_utc=manifest.created_at_utc,
            )
        )
        capture_option_values.add("Source Evidence release readiness metadata")
    if source_adapter_audit_registry_metadata is not None:
        audit_metadata = _value_for_dict(source_adapter_audit_registry_metadata)
        assets.append(
            _metadata_asset(
                asset_type=ASSET_RAW_SIDECAR,
                description=(
                    "Source Adapter audit registry metadata sidecar: method audit "
                    "rows remain review-required and not live-executed."
                ),
                metadata=audit_metadata,
                created_at_utc=manifest.created_at_utc,
            )
        )
        capture_option_values.add("Source Adapter audit registry metadata")
    if source_site_method_audit_registry_metadata is not None:
        site_method_metadata = _value_for_dict(source_site_method_audit_registry_metadata)
        assets.append(
            _metadata_asset(
                asset_type=ASSET_RAW_SIDECAR,
                description=(
                    "Source site/method audit registry metadata sidecar: selector "
                    "audit rows remain review-required and not live-executed."
                ),
                metadata=site_method_metadata,
                created_at_utc=manifest.created_at_utc,
            )
        )
        capture_option_values.add("Source site/method audit registry metadata")
    capture_options = sorted(capture_option_values)
    notes = manifest.notes
    if "Source Evidence workflow state metadata sidecar included." not in notes:
        notes = (notes + "\n" if notes else "") + "Source Evidence workflow state metadata sidecar included."
    if (
        release_readiness_metadata is not None
        and "Source Evidence release readiness metadata sidecar included." not in notes
    ):
        notes = (
            notes + "\n" if notes else ""
        ) + "Source Evidence release readiness metadata sidecar included."
    if (
        source_adapter_audit_registry_metadata is not None
        and "Source Adapter audit registry metadata sidecar included." not in notes
    ):
        notes = (
            notes + "\n" if notes else ""
        ) + "Source Adapter audit registry metadata sidecar included."
    if (
        source_site_method_audit_registry_metadata is not None
        and "Source site/method audit registry metadata sidecar included." not in notes
    ):
        notes = (
            notes + "\n" if notes else ""
        ) + "Source site/method audit registry metadata sidecar included."
    return TotalExportManifest(
        package_id=manifest.package_id,
        created_at_utc=manifest.created_at_utc,
        source_urls=list(manifest.source_urls),
        output_folder=manifest.output_folder,
        capture_options=capture_options,
        assets=assets,
        provenance_records=list(manifest.provenance_records),
        claim_notes=list(manifest.claim_notes),
        media_source_chain_notes=list(manifest.media_source_chain_notes),
        archive_results=list(manifest.archive_results),
        notes=notes,
        app_version=manifest.app_version,
    )


def source_evidence_review_manifest_to_json(manifest: TotalExportManifest) -> str:
    return json.dumps(manifest.to_dict(), indent=2, sort_keys=True)
