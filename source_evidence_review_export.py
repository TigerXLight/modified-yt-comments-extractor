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


def source_evidence_review_manifest_to_json(manifest: TotalExportManifest) -> str:
    return json.dumps(manifest.to_dict(), indent=2, sort_keys=True)
