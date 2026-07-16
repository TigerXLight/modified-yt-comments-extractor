from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evidence_database_index import (
    EVIDENCE_DATABASE_INDEX_SCOPE,
    EvidenceClassificationValue,
    EvidenceDatabaseRoot,
    EvidenceIndexManifest,
    EvidenceIndexRecord,
    EvidenceTaxonomyVersion,
    evidence_index_manifest_from_dict,
    stable_json_dumps,
)
from evidence_database_review import (
    EVIDENCE_DATABASE_REVIEW_SCOPE,
    EvidenceDatabaseApplyPlan,
    EvidenceDatabaseApplyPlanEntry,
    EvidenceDatabasePreviewRequest,
    EvidenceDatabasePreviewResult,
    EvidenceDatabasePreviewRow,
    EvidenceDatabaseReviewDecision,
    EvidenceDatabaseReviewDecisionType,
    EvidenceDatabaseReviewSession,
)


EVIDENCE_DATABASE_REVIEW_EXPORT_SCHEMA_VERSION = "evidence-database-review-export-v1"
EVIDENCE_DATABASE_REVIEW_EXPORT_SCOPE = (
    "local evidence database review session import/export only; JSON only; "
    "explicit records only; no broad folder scanning, no file movement, no "
    "automatic classification execution, no sensitive-attribute inference, no "
    "network, no provider calls, no credentials"
)
REVIEW_IMPORT_STATUS_OK = "ok"
REVIEW_IMPORT_STATUS_INVALID = "invalid"


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


@dataclass(frozen=True)
class EvidenceDatabaseReviewImportBundle:
    session: EvidenceDatabaseReviewSession
    preview_request: EvidenceDatabasePreviewRequest
    preview_result: EvidenceDatabasePreviewResult
    decisions: tuple[EvidenceDatabaseReviewDecision, ...]
    apply_plan: EvidenceDatabaseApplyPlan
    index_manifest: EvidenceIndexManifest
    payload_sha256: str
    schema_version: str = EVIDENCE_DATABASE_REVIEW_EXPORT_SCHEMA_VERSION
    scope: str = EVIDENCE_DATABASE_REVIEW_EXPORT_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "apply_plan": self.apply_plan.to_dict(),
            "decisions": [decision.to_dict() for decision in self.decisions],
            "index_manifest": self.index_manifest.to_dict(),
            "payload_sha256": self.payload_sha256,
            "preview_request": self.preview_request.to_dict(),
            "preview_result": self.preview_result.to_dict(),
            "schema_version": self.schema_version,
            "scope": self.scope,
            "session": self.session.to_dict(),
        }


@dataclass(frozen=True)
class EvidenceDatabaseReviewImportResult:
    status: str
    bundle: EvidenceDatabaseReviewImportBundle | None = None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = EVIDENCE_DATABASE_REVIEW_EXPORT_SCHEMA_VERSION
    scope: str = EVIDENCE_DATABASE_REVIEW_EXPORT_SCOPE

    @property
    def ok(self) -> bool:
        return self.status == REVIEW_IMPORT_STATUS_OK

    def to_dict(self) -> dict[str, Any]:
        return {
            "errors": list(self.errors),
            "ok": self.ok,
            "payload_sha256": self.bundle.payload_sha256 if self.bundle else "",
            "schema_version": self.schema_version,
            "scope": self.scope,
            "status": self.status,
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


def _enum_classification(value: Any) -> EvidenceClassificationValue:
    text = str(value or "").strip()
    for item in EvidenceClassificationValue:
        if item.value == text:
            return item
    return EvidenceClassificationValue.UNKNOWN


def _enum_decision(value: Any) -> EvidenceDatabaseReviewDecisionType:
    text = str(value or "").strip()
    for item in EvidenceDatabaseReviewDecisionType:
        if item.value == text:
            return item
    return EvidenceDatabaseReviewDecisionType.MARK_UNKNOWN


def _tuple_str(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    if value:
        return (str(value),)
    return ()


def _bool(value: Any) -> bool:
    return bool(value)


def _secret_like_keys(data: Any, *, prefix: str = "") -> tuple[str, ...]:
    blocked = ("api_key", "authorization", "cookie", "password", "secret", "token")
    found: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            key_text = str(key)
            path = f"{prefix}.{key_text}" if prefix else key_text
            if any(blocked_item in key_text.lower() for blocked_item in blocked):
                found.append(path)
            found.extend(_secret_like_keys(value, prefix=path))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            found.extend(_secret_like_keys(value, prefix=f"{prefix}[{index}]"))
    return tuple(found)


def validate_evidence_database_review_export_payload(payload: Any) -> tuple[str, ...]:
    if not isinstance(payload, dict):
        return ("payload_not_object",)
    errors: list[str] = []
    if payload.get("schema_version") != EVIDENCE_DATABASE_REVIEW_EXPORT_SCHEMA_VERSION:
        errors.append("unsupported_schema_version")
    if payload.get("scope") != EVIDENCE_DATABASE_REVIEW_EXPORT_SCOPE:
        errors.append("unexpected_scope")
    payload_hash = str(payload.get("payload_sha256", ""))
    payload_without_hash = dict(payload)
    payload_without_hash.pop("payload_sha256", None)
    if not payload_hash or payload_hash != _payload_hash(payload_without_hash):
        errors.append("payload_sha256_mismatch")
    if _secret_like_keys(payload):
        errors.append("secret_like_key_present")

    session = payload.get("session", {})
    if not isinstance(session, dict):
        errors.append("session_not_object")
        session = {}
    if not _bool(session.get("dry_run_only", False)):
        errors.append("session_not_dry_run_only")
    if _bool(session.get("destructive_actions_enabled", False)):
        errors.append("session_destructive_actions_enabled")
    if _bool(session.get("broad_scan_allowed", False)):
        errors.append("session_broad_scan_allowed")

    preview_request = payload.get("preview_request", {})
    if not isinstance(preview_request, dict):
        errors.append("preview_request_not_object")
        preview_request = {}
    if not _bool(preview_request.get("supplied_records_only", False)):
        errors.append("preview_request_not_supplied_records_only")
    if _bool(preview_request.get("broad_scan_requested", False)):
        errors.append("preview_request_broad_scan_requested")

    preview_result = payload.get("preview_result", {})
    if not isinstance(preview_result, dict):
        errors.append("preview_result_not_object")
        preview_result = {}
    if not _bool(preview_result.get("supplied_records_only", False)):
        errors.append("preview_result_not_supplied_records_only")
    if _bool(preview_result.get("broad_scan_performed", False)):
        errors.append("preview_result_broad_scan_performed")
    if _bool(preview_result.get("file_operation_performed", False)):
        errors.append("preview_result_file_operation_performed")

    apply_plan = payload.get("apply_plan", {})
    if not isinstance(apply_plan, dict):
        errors.append("apply_plan_not_object")
        apply_plan = {}
    if not _bool(apply_plan.get("dry_run", False)):
        errors.append("apply_plan_not_dry_run")
    if _bool(apply_plan.get("execute_file_moves", False)):
        errors.append("apply_plan_execute_file_moves")
    if _bool(apply_plan.get("execute_classification_changes", False)):
        errors.append("apply_plan_execute_classification_changes")
    if _bool(apply_plan.get("file_operation_performed", False)):
        errors.append("apply_plan_file_operation_performed")
    if not _bool(apply_plan.get("destructive_action_not_implemented", False)):
        errors.append("apply_plan_destructive_action_available")
    for entry in apply_plan.get("entries", []):
        if not isinstance(entry, dict):
            errors.append("apply_plan_entry_not_object")
            continue
        if _bool(entry.get("file_operation_performed", False)):
            errors.append("apply_plan_entry_file_operation_performed")
        if _bool(entry.get("classification_change_executed", False)):
            errors.append("apply_plan_entry_classification_change_executed")

    index_manifest = payload.get("index_manifest", {})
    if not isinstance(index_manifest, dict):
        errors.append("index_manifest_not_object")
        index_manifest = {}
    for root in index_manifest.get("database_roots", []):
        if not isinstance(root, dict):
            errors.append("index_root_not_object")
            continue
        if _bool(root.get("broad_scan_allowed", False)):
            errors.append("index_root_broad_scan_allowed")
        if not _bool(root.get("dry_run_required", False)):
            errors.append("index_root_not_dry_run_required")
        if not _bool(root.get("moves_require_explicit_approval", False)):
            errors.append("index_root_moves_without_approval")
    for record in index_manifest.get("records", []):
        if not isinstance(record, dict):
            errors.append("index_record_not_object")
            continue
        identity = record.get("identity", {})
        if not isinstance(identity, dict):
            errors.append("index_record_identity_not_object")
        elif not str(identity.get("item_id", "")).strip():
            errors.append("index_record_missing_item_id")
        classification_state = record.get("classification_state", {})
        if not isinstance(classification_state, dict):
            errors.append("index_record_classification_state_not_object")
        for path in record.get("path_records", []):
            if isinstance(path, dict) and _bool(path.get("file_operation_performed", False)):
                errors.append("index_path_file_operation_performed")
        for proposal_key in ("placement_proposals", "reclassification_proposals"):
            for proposal in record.get(proposal_key, []):
                if isinstance(proposal, dict) and _bool(proposal.get("file_operation_performed", False)):
                    errors.append(f"index_{proposal_key}_file_operation_performed")
    return tuple(dict.fromkeys(errors))


def _preview_row_from_dict(data: dict[str, Any]) -> EvidenceDatabasePreviewRow:
    return EvidenceDatabasePreviewRow(
        item_id=str(data.get("item_id", "")),
        display_name=str(data.get("display_name", "")),
        classification_value=_enum_classification(data.get("classification_value", "")),
        database_root_id=str(data.get("database_root_id", "")),
        taxonomy_version_id=str(data.get("taxonomy_version_id", "")),
        placement_proposal_count=int(data.get("placement_proposal_count", 0) or 0),
        reclassification_proposal_count=int(data.get("reclassification_proposal_count", 0) or 0),
        user_confirmation_required=_bool(data.get("user_confirmation_required", True)),
        warnings=_tuple_str(data.get("warnings", ())),
    )


def _decision_from_dict(data: dict[str, Any]) -> EvidenceDatabaseReviewDecision:
    return EvidenceDatabaseReviewDecision(
        decision_type=_enum_decision(data.get("decision_type", "")),
        item_id=str(data.get("item_id", "")),
        proposal_id=str(data.get("proposal_id", "")),
        target_classification_value=_enum_classification(
            data.get("target_classification_value", "")
        ),
        note=str(data.get("note", "")),
        user_confirmed=_bool(data.get("user_confirmed", False)),
        decision_id=str(data.get("decision_id", "")),
        created_at_utc=str(data.get("created_at_utc", "")),
        scope=str(data.get("scope", EVIDENCE_DATABASE_REVIEW_SCOPE)),
    )


def _apply_entry_from_dict(data: dict[str, Any]) -> EvidenceDatabaseApplyPlanEntry:
    return EvidenceDatabaseApplyPlanEntry(
        decision_id=str(data.get("decision_id", "")),
        item_id=str(data.get("item_id", "")),
        decision_type=_enum_decision(data.get("decision_type", "")),
        previous_path=str(data.get("previous_path", "")),
        proposed_path=str(data.get("proposed_path", "")),
        previous_classification_value=_enum_classification(
            data.get("previous_classification_value", "")
        ),
        target_classification_value=_enum_classification(
            data.get("target_classification_value", "")
        ),
        old_new_path_history_preserved=_bool(
            data.get("old_new_path_history_preserved", True)
        ),
        file_operation_performed=_bool(data.get("file_operation_performed", False)),
        classification_change_executed=_bool(
            data.get("classification_change_executed", False)
        ),
        user_confirmation_required=_bool(data.get("user_confirmation_required", True)),
        note=str(data.get("note", "")),
    )


def import_evidence_database_review_export_payload(
    payload: Any,
) -> EvidenceDatabaseReviewImportResult:
    errors = validate_evidence_database_review_export_payload(payload)
    if errors:
        return EvidenceDatabaseReviewImportResult(
            status=REVIEW_IMPORT_STATUS_INVALID,
            errors=errors,
        )
    assert isinstance(payload, dict)
    session_data = payload["session"]
    preview_request_data = payload["preview_request"]
    preview_result_data = payload["preview_result"]
    apply_plan_data = payload["apply_plan"]
    decision_data = payload.get("decisions", [])

    session = EvidenceDatabaseReviewSession(
        session_id=str(session_data.get("session_id", "")),
        selected_root_id=str(session_data.get("selected_root_id", "")),
        taxonomy_version_id=str(session_data.get("taxonomy_version_id", "")),
        registered_root_ids=_tuple_str(session_data.get("registered_root_ids", ())),
        review_mode=str(session_data.get("review_mode", "dry_run_review")),
        dry_run_only=True,
        user_confirmation_required=_bool(
            session_data.get("user_confirmation_required", True)
        ),
        destructive_actions_enabled=False,
        broad_scan_allowed=False,
        created_at_utc=str(session_data.get("created_at_utc", "")),
        scope=str(session_data.get("scope", EVIDENCE_DATABASE_REVIEW_SCOPE)),
    )
    preview_request = EvidenceDatabasePreviewRequest(
        session_id=str(preview_request_data.get("session_id", "")),
        root_id=str(preview_request_data.get("root_id", "")),
        record_ids=_tuple_str(preview_request_data.get("record_ids", ())),
        include_classification_values=_tuple_str(
            preview_request_data.get("include_classification_values", ())
        ),
        supplied_records_only=True,
        broad_scan_requested=False,
        request_id=str(preview_request_data.get("request_id", "")),
        created_at_utc=str(preview_request_data.get("created_at_utc", "")),
        scope=str(preview_request_data.get("scope", EVIDENCE_DATABASE_REVIEW_SCOPE)),
    )
    grouped = {
        str(key): tuple(str(item) for item in value)
        for key, value in preview_result_data.get("grouped_record_ids", {}).items()
        if isinstance(value, list)
    }
    rows = tuple(
        _preview_row_from_dict(row)
        for row in preview_result_data.get("rows", [])
        if isinstance(row, dict)
    )
    preview_result = EvidenceDatabasePreviewResult(
        request_id=str(preview_result_data.get("request_id", "")),
        grouped_record_ids=grouped,
        rows=rows,
        record_count=int(preview_result_data.get("record_count", len(rows)) or 0),
        supplied_records_only=True,
        broad_scan_performed=False,
        file_operation_performed=False,
        warnings=_tuple_str(preview_result_data.get("warnings", ())),
        created_at_utc=str(preview_result_data.get("created_at_utc", "")),
        scope=str(preview_result_data.get("scope", EVIDENCE_DATABASE_REVIEW_SCOPE)),
    )
    decisions = tuple(
        _decision_from_dict(decision)
        for decision in decision_data
        if isinstance(decision, dict)
    )
    entries = tuple(
        _apply_entry_from_dict(entry)
        for entry in apply_plan_data.get("entries", [])
        if isinstance(entry, dict)
    )
    apply_plan = EvidenceDatabaseApplyPlan(
        plan_id=str(apply_plan_data.get("plan_id", "")),
        session_id=str(apply_plan_data.get("session_id", "")),
        decisions=decisions,
        entries=entries,
        dry_run=True,
        execute_file_moves=False,
        execute_classification_changes=False,
        file_operation_performed=False,
        destructive_action_not_implemented=True,
        user_confirmation_required=_bool(
            apply_plan_data.get("user_confirmation_required", True)
        ),
        warnings=_tuple_str(apply_plan_data.get("warnings", ())),
        created_at_utc=str(apply_plan_data.get("created_at_utc", "")),
        scope=str(apply_plan_data.get("scope", EVIDENCE_DATABASE_REVIEW_SCOPE)),
    )
    index_manifest = evidence_index_manifest_from_dict(payload["index_manifest"])
    bundle = EvidenceDatabaseReviewImportBundle(
        session=session,
        preview_request=preview_request,
        preview_result=preview_result,
        decisions=decisions,
        apply_plan=apply_plan,
        index_manifest=index_manifest,
        payload_sha256=str(payload.get("payload_sha256", "")),
    )
    return EvidenceDatabaseReviewImportResult(
        status=REVIEW_IMPORT_STATUS_OK,
        bundle=bundle,
    )


def read_evidence_database_review_export_file(
    export_path: str,
) -> EvidenceDatabaseReviewImportResult:
    try:
        payload = json.loads(Path(export_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return EvidenceDatabaseReviewImportResult(
            status=REVIEW_IMPORT_STATUS_INVALID,
            errors=("read_or_json_parse_failed",),
        )
    return import_evidence_database_review_export_payload(payload)
