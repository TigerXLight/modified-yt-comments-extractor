from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evidence_database_index import (
    EVIDENCE_DATABASE_INDEX_SCOPE,
    EvidenceDatabaseRoot,
    EvidenceIndexManifest,
    EvidenceIndexRecord,
    EvidenceTaxonomyVersion,
    stable_json_dumps,
)
from evidence_database_review import (
    EVIDENCE_DATABASE_REVIEW_SCOPE,
    EvidenceDatabaseApplyPlan,
    EvidenceDatabasePreviewRequest,
    EvidenceDatabasePreviewResult,
    EvidenceDatabaseReviewDecision,
    EvidenceDatabaseReviewSession,
)


EVIDENCE_DATABASE_REVIEW_EXPORT_SCHEMA_VERSION = "evidence-database-review-export-v1"
EVIDENCE_DATABASE_REVIEW_EXPORT_SCOPE = (
    "local evidence database review session import/export only; JSON only; "
    "explicit records only; no broad folder scanning, no file movement, no "
    "automatic classification execution, no sensitive-attribute inference, no "
    "network, no provider calls, no credentials"
)


@dataclass(frozen=True)
class EvidenceDatabaseReviewExportResult:
    export_path: str
    payload_sha256: str
    byte_count: int
    schema_version: str = EVIDENCE_DATABASE_REVIEW_EXPORT_SCHEMA_VERSION
    warnings: tuple[str, ...] = ()
    scope: str = EVIDENCE_DATABASE_REVIEW_EXPORT_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "byte_count": self.byte_count,
            "export_path": self.export_path,
            "payload_sha256": self.payload_sha256,
            "schema_version": self.schema_version,
            "scope": self.scope,
            "warnings": list(self.warnings),
        }


def _payload_hash(payload_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload_without_hash).encode("utf-8")).hexdigest()


def _index_manifest_payload(
    *,
    roots: tuple[EvidenceDatabaseRoot, ...],
    taxonomy_versions: tuple[EvidenceTaxonomyVersion, ...],
    records: tuple[EvidenceIndexRecord, ...],
    manifest_id: str,
) -> dict[str, Any]:
    manifest = EvidenceIndexManifest(
        manifest_id=manifest_id,
        database_roots=roots,
        taxonomy_versions=taxonomy_versions,
        records=records,
        payload_sha256="",
        scope=EVIDENCE_DATABASE_INDEX_SCOPE,
    )
    return manifest.to_dict()


def build_evidence_database_review_export_payload(
    *,
    session: EvidenceDatabaseReviewSession,
    preview_request: EvidenceDatabasePreviewRequest,
    preview_result: EvidenceDatabasePreviewResult,
    decisions: tuple[EvidenceDatabaseReviewDecision, ...],
    apply_plan: EvidenceDatabaseApplyPlan,
    roots: tuple[EvidenceDatabaseRoot, ...] = (),
    taxonomy_versions: tuple[EvidenceTaxonomyVersion, ...] = (),
    records: tuple[EvidenceIndexRecord, ...] = (),
    export_id: str = "evidence_database_review_export",
) -> dict[str, Any]:
    payload_without_hash: dict[str, Any] = {
        "apply_plan": apply_plan.to_dict(),
        "decisions": [decision.to_dict() for decision in decisions],
        "export_id": export_id,
        "index_manifest": _index_manifest_payload(
            roots=roots,
            taxonomy_versions=taxonomy_versions,
            records=records,
            manifest_id=f"{export_id}_index_manifest",
        ),
        "preview_request": preview_request.to_dict(),
        "preview_result": preview_result.to_dict(),
        "schema_version": EVIDENCE_DATABASE_REVIEW_EXPORT_SCHEMA_VERSION,
        "scope": EVIDENCE_DATABASE_REVIEW_EXPORT_SCOPE,
        "session": session.to_dict(),
    }
    payload = dict(payload_without_hash)
    payload["payload_sha256"] = _payload_hash(payload_without_hash)
    return payload


def evidence_database_review_export_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_evidence_database_review_export_file(
    *,
    export_path: str,
    session: EvidenceDatabaseReviewSession,
    preview_request: EvidenceDatabasePreviewRequest,
    preview_result: EvidenceDatabasePreviewResult,
    decisions: tuple[EvidenceDatabaseReviewDecision, ...],
    apply_plan: EvidenceDatabaseApplyPlan,
    roots: tuple[EvidenceDatabaseRoot, ...] = (),
    taxonomy_versions: tuple[EvidenceTaxonomyVersion, ...] = (),
    records: tuple[EvidenceIndexRecord, ...] = (),
    export_id: str = "evidence_database_review_export",
) -> EvidenceDatabaseReviewExportResult:
    payload = build_evidence_database_review_export_payload(
        session=session,
        preview_request=preview_request,
        preview_result=preview_result,
        decisions=decisions,
        apply_plan=apply_plan,
        roots=roots,
        taxonomy_versions=taxonomy_versions,
        records=records,
        export_id=export_id,
    )
    output = evidence_database_review_export_json(payload)
    path = Path(export_path)
    path.write_text(output, encoding="utf-8")
    return EvidenceDatabaseReviewExportResult(
        export_path=str(path),
        payload_sha256=str(payload["payload_sha256"]),
        byte_count=len(output.encode("utf-8")),
    )
