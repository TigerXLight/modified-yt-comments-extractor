from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "source_pipeline_closeout_v1"
STAGE_INVENTORY_SCHEMA_VERSION = "source_pipeline_stage_inventory_v1"
ROADMAP_HANDOFF_SCHEMA_VERSION = "source_pipeline_roadmap_closeout_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_pipeline_closeout_operator_summary_v1"

_ALLOWED_ARCHIVE_DECISIONS = {"APPROVED", "REJECTED", "REVISION_REQUESTED"}
_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}

PIPELINE_STAGES: tuple[dict[str, str], ...] = (
    {"stage_id": "source_discovery", "label": "Source discovery", "shared_module": "source_adapter_coverage"},
    {"stage_id": "lightweight_browser_capture", "label": "Lightweight in-app browser capture", "shared_module": "lightweight_in_app_browser_capture"},
    {"stage_id": "artifact_collection", "label": "Explicit artifact collection", "shared_module": "source_artifact_collection"},
    {"stage_id": "content_extraction", "label": "Article/content extraction", "shared_module": "source_content_extraction"},
    {"stage_id": "comments_extraction", "label": "Comments/replies extraction", "shared_module": "source_comment_extraction"},
    {"stage_id": "capture_bundle", "label": "Capture bundle", "shared_module": "source_capture_bundle"},
    {"stage_id": "total_export_package", "label": "Total Export package", "shared_module": "source_total_export_package"},
    {"stage_id": "evidence_queue", "label": "Evidence Queue integration", "shared_module": "source_evidence_queue"},
    {"stage_id": "evidence_review", "label": "Evidence Review package/decision", "shared_module": "source_evidence_review"},
    {"stage_id": "approved_release", "label": "Approved release package", "shared_module": "source_approved_release"},
    {"stage_id": "release_index", "label": "Release index/export bundle", "shared_module": "source_release_index"},
    {"stage_id": "release_audit", "label": "Release audit/traceability", "shared_module": "source_release_audit"},
    {"stage_id": "archive_handoff", "label": "Manual archive handoff", "shared_module": "source_archive_handoff"},
    {"stage_id": "archive_result_intake", "label": "Manual archive result intake", "shared_module": "source_archive_result_intake"},
    {"stage_id": "archive_review", "label": "Archive review package/decision", "shared_module": "source_archive_review"},
)


class SourcePipelineCloseoutError(ValueError):
    """Raised when source pipeline closeout input is invalid."""


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _stable_hash(data: Mapping[str, Any], *, length: int = 12) -> str:
    return hashlib.sha256(_json_bytes(data)).hexdigest()[:length]


def _clean_identifier(value: object, *, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    text = _SAFE_ID_RE.sub(".", text).strip("._-")
    return text or fallback


def _coerce_mapping(value: Mapping[str, Any] | None, *, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a JSON object")
    return dict(value)


def _ensure_no_local_paths(value: Mapping[str, Any], *, name: str) -> None:
    present = sorted(_FORBIDDEN_PATH_FIELDS.intersection(value.keys()))
    if present:
        raise SourcePipelineCloseoutError(f"{name} must not include local path fields: {', '.join(present)}")


def _first_text(*values: object, required: bool = False, field_name: str = "value") -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    if required:
        raise SourcePipelineCloseoutError(f"{field_name} is required")
    return ""


def _normalise_notes(*sources: Iterable[str] | None) -> list[str]:
    notes: list[str] = []
    seen: set[str] = set()
    for source in sources:
        if not source:
            continue
        for raw in source:
            text = str(raw or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            notes.append(text)
    return notes


def _normalise_decision(value: object) -> str:
    decision = str(value or "").strip().upper()
    if decision not in _ALLOWED_ARCHIVE_DECISIONS:
        raise SourcePipelineCloseoutError("archive review decision must be APPROVED, REJECTED, or REVISION_REQUESTED")
    return decision


def _source_artifacts_from_package(package: Mapping[str, Any]) -> list[dict[str, Any]]:
    artifacts = package.get("source_artifacts") or package.get("artifacts") or []
    if artifacts is None:
        return []
    if not isinstance(artifacts, list):
        raise TypeError("source_artifacts/artifacts must be a list when present")

    normalised: list[dict[str, Any]] = []
    for index, raw_artifact in enumerate(artifacts):
        if not isinstance(raw_artifact, Mapping):
            raise TypeError(f"source artifact {index} must be a JSON object")
        artifact = dict(raw_artifact)
        _ensure_no_local_paths(artifact, name=f"source artifact {index}")
        filename = _first_text(artifact.get("filename"), artifact.get("basename"), field_name=f"source artifact {index}.filename")
        if "/" in filename or "\\" in filename or ":" in filename:
            raise SourcePipelineCloseoutError("source artifact filenames must be safe basenames, not paths")
        normalised.append(
            {
                "role": _clean_identifier(artifact.get("role"), fallback="source_artifact"),
                "filename": filename,
                "sha256": _first_text(artifact.get("sha256"), artifact.get("hash")),
                "byte_count": int(artifact.get("byte_count") or 0),
            }
        )
    return normalised


def _receipt_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    entries = record.get("reviewed_receipts") or record.get("archive_receipts") or record.get("receipts") or []
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        raise TypeError("archive receipt entries must be a list when present")

    providers: list[str] = []
    archive_urls: list[str] = []
    for index, raw_entry in enumerate(entries):
        if not isinstance(raw_entry, Mapping):
            raise TypeError(f"archive receipt entry {index} must be a JSON object")
        entry = dict(raw_entry)
        _ensure_no_local_paths(entry, name=f"archive receipt entry {index}")
        provider_id = _clean_identifier(entry.get("provider_id"), fallback="archive_provider")
        if provider_id not in providers:
            providers.append(provider_id)
        archive_url = str(entry.get("archive_url") or "").strip()
        if archive_url:
            if not _URL_RE.match(archive_url):
                raise SourcePipelineCloseoutError(f"archive receipt entry {index}.archive_url must start with http:// or https://")
            archive_urls.append(archive_url)

    return {
        "receipt_count": len(entries),
        "provider_ids": providers,
        "archive_url_count": len(archive_urls),
        "archive_urls": archive_urls,
    }


def _stage_inventory(*, final_status: str, archive_decision: str, stage_status_overrides: Mapping[str, str] | None) -> dict[str, Any]:
    overrides = dict(stage_status_overrides or {})
    stages: list[dict[str, Any]] = []
    for position, stage in enumerate(PIPELINE_STAGES, start=1):
        stage_id = stage["stage_id"]
        default_status = "COMPLETE" if final_status == "SOURCE_PIPELINE_COMPLETE" else "FOLLOW_UP_REQUIRED"
        status = str(overrides.get(stage_id) or default_status).strip().upper()
        stages.append(
            {
                "position": position,
                "stage_id": stage_id,
                "label": stage["label"],
                "shared_module": stage["shared_module"],
                "status": status,
                "adapter_specific_module_required": False,
            }
        )

    complete_count = sum(1 for stage in stages if stage["status"] == "COMPLETE")
    return {
        "schema_version": STAGE_INVENTORY_SCHEMA_VERSION,
        "stage_count": len(stages),
        "complete_stage_count": complete_count,
        "follow_up_stage_count": len(stages) - complete_count,
        "archive_decision": archive_decision,
        "final_status": final_status,
        "coverage_strategy": "one_framework_many_adapters",
        "stages": stages,
    }


def build_source_pipeline_closeout(
    archive_review_package: Mapping[str, Any],
    *,
    archive_review_decision: Mapping[str, Any] | None = None,
    archive_review_closeout: Mapping[str, Any] | None = None,
    stage_status_overrides: Mapping[str, str] | None = None,
    operator_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    package = _coerce_mapping(archive_review_package, name="archive_review_package")
    decision_record = _coerce_mapping(archive_review_decision, name="archive_review_decision")
    closeout_record = _coerce_mapping(archive_review_closeout, name="archive_review_closeout")
    _ensure_no_local_paths(package, name="archive_review_package")
    _ensure_no_local_paths(decision_record, name="archive_review_decision")
    _ensure_no_local_paths(closeout_record, name="archive_review_closeout")

    adapter_id = _clean_identifier(
        _first_text(package.get("adapter_id"), decision_record.get("adapter_id"), closeout_record.get("adapter_id"), required=True, field_name="adapter_id"),
        fallback="source_adapter",
    )
    source_url = _first_text(package.get("source_url"), decision_record.get("source_url"), closeout_record.get("source_url"), required=True, field_name="source_url")
    if not _URL_RE.match(source_url):
        raise SourcePipelineCloseoutError("source_url must start with http:// or https://")

    archive_review_package_id = _clean_identifier(
        _first_text(
            package.get("archive_review_package_id"),
            package.get("source_archive_review_package_id"),
            decision_record.get("archive_review_package_id"),
            closeout_record.get("archive_review_package_id"),
            required=True,
            field_name="archive_review_package_id",
        ),
        fallback="archive_review_package",
    )
    archive_review_decision_id = _clean_identifier(
        _first_text(decision_record.get("archive_review_decision_id"), closeout_record.get("archive_review_decision_id"), archive_review_package_id),
        fallback="archive_review_decision",
    )
    archive_review_closeout_id = _clean_identifier(
        _first_text(closeout_record.get("archive_review_closeout_id"), closeout_record.get("closeout_id"), archive_review_package_id),
        fallback="archive_review_closeout",
    )

    archive_decision = _normalise_decision(
        _first_text(decision_record.get("decision"), closeout_record.get("decision"), package.get("decision"), required=True, field_name="decision")
    )
    closeout_status = str(
        _first_text(closeout_record.get("closeout_status"), closeout_record.get("status"), package.get("closeout_status"), field_name="closeout_status")
    ).strip().upper()
    final_status = "SOURCE_PIPELINE_COMPLETE" if archive_decision == "APPROVED" and closeout_status in {"", "ARCHIVE_COMPLETE", "SOURCE_PIPELINE_COMPLETE"} else "FOLLOW_UP_REQUIRED"

    ids = {
        "queue_item_id": _clean_identifier(_first_text(package.get("queue_item_id"), decision_record.get("queue_item_id"), closeout_record.get("queue_item_id")), fallback="evidence_queue"),
        "total_export_package_id": _clean_identifier(_first_text(package.get("total_export_package_id"), decision_record.get("total_export_package_id"), closeout_record.get("total_export_package_id")), fallback="total_export_package"),
        "approved_release_id": _clean_identifier(_first_text(package.get("approved_release_id"), decision_record.get("approved_release_id"), closeout_record.get("approved_release_id")), fallback="approved_release"),
        "release_index_id": _clean_identifier(_first_text(package.get("release_index_id"), decision_record.get("release_index_id"), closeout_record.get("release_index_id")), fallback="release_index"),
        "release_audit_id": _clean_identifier(_first_text(package.get("release_audit_id"), decision_record.get("release_audit_id"), closeout_record.get("release_audit_id")), fallback="release_audit"),
        "archive_handoff_id": _clean_identifier(_first_text(package.get("archive_handoff_id"), decision_record.get("archive_handoff_id"), closeout_record.get("archive_handoff_id")), fallback="archive_handoff"),
        "archive_result_intake_id": _clean_identifier(_first_text(package.get("archive_result_intake_id"), decision_record.get("archive_result_intake_id"), closeout_record.get("archive_result_intake_id")), fallback="archive_result_intake"),
        "archive_review_package_id": archive_review_package_id,
        "archive_review_decision_id": archive_review_decision_id,
        "archive_review_closeout_id": archive_review_closeout_id,
    }

    source_artifacts = _source_artifacts_from_package(package)
    receipts = _receipt_summary(package)
    notes = _normalise_notes(package.get("operator_notes"), decision_record.get("operator_notes"), closeout_record.get("operator_notes"), operator_notes)

    seed = {
        "schema_version": SCHEMA_VERSION,
        "adapter_id": adapter_id,
        "source_url": source_url,
        "archive_review_package_id": archive_review_package_id,
        "archive_review_decision_id": archive_review_decision_id,
        "archive_review_closeout_id": archive_review_closeout_id,
        "archive_decision": archive_decision,
        "final_status": final_status,
        "ids": ids,
        "receipt_count": receipts["receipt_count"],
        "source_artifact_count": len(source_artifacts),
    }
    closeout_id = f"{adapter_id}.source_pipeline_closeout.{_stable_hash(seed)}"

    inventory = _stage_inventory(final_status=final_status, archive_decision=archive_decision, stage_status_overrides=stage_status_overrides)
    closeout_report = {
        "schema_version": SCHEMA_VERSION,
        "source_pipeline_closeout_id": closeout_id,
        "adapter_id": adapter_id,
        "source_url": source_url,
        "final_status": final_status,
        "archive_decision": archive_decision,
        "archive_review_package_id": archive_review_package_id,
        "archive_review_decision_id": archive_review_decision_id,
        "archive_review_closeout_id": archive_review_closeout_id,
        "pipeline_ids": ids,
        "stage_count": inventory["stage_count"],
        "complete_stage_count": inventory["complete_stage_count"],
        "follow_up_stage_count": inventory["follow_up_stage_count"],
        "source_artifact_count": len(source_artifacts),
        "source_artifacts": source_artifacts,
        "archive_receipt_summary": receipts,
        "operator_notes": notes,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "operator_action_required": final_status != "SOURCE_PIPELINE_COMPLETE",
    }
    roadmap_handoff = {
        "schema_version": ROADMAP_HANDOFF_SCHEMA_VERSION,
        "source_pipeline_closeout_id": closeout_id,
        "adapter_id": adapter_id,
        "source_url": source_url,
        "final_status": final_status,
        "coverage_strategy": "one_framework_many_adapters",
        "closed_shared_stages": [stage["stage_id"] for stage in inventory["stages"] if stage["status"] == "COMPLETE"],
        "remaining_follow_up_stages": [stage["stage_id"] for stage in inventory["stages"] if stage["status"] != "COMPLETE"],
        "next_shared_work": [
            "Add adapter specs and fixture matrices for each source type without cloning MSN modules.",
            "Wire adapter mappings into the shared stage contracts only where the fixture matrix proves coverage.",
            "Keep live/browser/archive operations operator-approved and manual by default.",
        ],
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "source_pipeline_closeout_id": closeout_id,
        "adapter_id": adapter_id,
        "source_url": source_url,
        "status": final_status,
        "archive_decision": archive_decision,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "operator_action_required": final_status != "SOURCE_PIPELINE_COMPLETE",
        "next_actions": roadmap_handoff["next_shared_work"] if final_status == "SOURCE_PIPELINE_COMPLETE" else ["Resolve archive review follow-up state before closing the pipeline."],
    }
    return {
        "closeout_report": closeout_report,
        "stage_inventory": inventory,
        "roadmap_closeout_handoff": roadmap_handoff,
        "operator_summary": operator_summary,
    }


def read_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return data
