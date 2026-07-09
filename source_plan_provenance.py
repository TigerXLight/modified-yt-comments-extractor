from __future__ import annotations

from dataclasses import replace

from evidence_schema import (
    CaptureMethod,
    EvidenceProvenance,
    PrimarySourceStatus,
    SourceRole,
)
from source_capture_plan import SourceCapturePlan
from total_export_manifest import TotalExportManifest


def provenance_from_source_capture_plan(plan: SourceCapturePlan) -> EvidenceProvenance:
    source_url = plan.normalized_url or plan.source_url
    verification_notes = f"Source Capture Plan status: {plan.status}; no fetch/capture performed."
    if plan.warnings:
        verification_notes = f"{verification_notes} Plan warnings: {'; '.join(plan.warnings)}"

    return EvidenceProvenance(
        source_url=source_url,
        canonical_url=plan.normalized_url,
        source_platform=plan.adapter_name,
        adapter_name=plan.adapter_name,
        capture_method=CaptureMethod.UNKNOWN,
        capture_purpose="Total Export source capture planning",
        source_role=SourceRole.UNKNOWN_SOURCE_ROLE,
        primary_source_status=PrimarySourceStatus.MANUAL_SOURCE_NOTE,
        item_id=plan.source_id,
        permalink=source_url,
        verification_notes=verification_notes,
    )


def manifest_with_plan_provenance(
    manifest: TotalExportManifest,
    plan: SourceCapturePlan,
) -> TotalExportManifest:
    provenance_records = list(manifest.provenance_records)
    provenance_records.append(provenance_from_source_capture_plan(plan))
    return replace(manifest, provenance_records=provenance_records)
