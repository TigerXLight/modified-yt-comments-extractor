from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "msn_manual_release_audit_report_v1"
AUDIT_STATUS_READY = "MSN_MANUAL_RELEASE_AUDIT_READY"
AUDIT_STATUS_REVIEW_REQUIRED = "MSN_MANUAL_RELEASE_AUDIT_REVIEW_REQUIRED"

_REQUIRED_STAGE_KEYS = (
    "manual_action_kit",
    "manual_artifact_collection",
    "msn_manual_capture_bundle",
    "total_export_package",
    "evidence_queue_item",
    "evidence_review_package",
    "evidence_review_decision",
    "approved_export_handoff",
    "approved_release_package",
    "release_index",
    "release_export_bundle",
    "release_section_closeout",
)

_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,220}$")
_ABSOLUTE_PATH_RE = re.compile(r"(?:[A-Za-z]:\\|[A-Za-z]:/|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")
_SECRET_FIELD_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)


def _hash_json(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _as_mapping(value: Mapping[str, Any] | str) -> dict[str, Any]:
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)


def _nested_values(value: Any) -> list[Any]:
    values: list[Any] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            values.append(key)
            values.extend(_nested_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_nested_values(item))
    else:
        values.append(value)
    return values


def _safe_text(value: Any, *, max_length: int = 400) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_length]


def _collect_stored_files(*reports: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    files: list[dict[str, Any]] = []
    for report in reports:
        if not report:
            continue
        for item in report.get("stored_files", []) or []:
            if not isinstance(item, Mapping):
                continue
            filename = str(item.get("filename", ""))
            role = str(item.get("role", ""))
            sha256 = str(item.get("sha256", ""))
            key = (filename, role, sha256)
            if not filename or not role or not sha256 or key in seen:
                continue
            seen.add(key)
            files.append(
                {
                    "filename": filename,
                    "role": role,
                    "sha256": sha256,
                    "byte_count": int(item.get("byte_count", 0) or 0),
                }
            )
    return files


def _stage_coverage(pipeline_closeout: Mapping[str, Any]) -> dict[str, bool]:
    explicit = pipeline_closeout.get("stage_coverage")
    if isinstance(explicit, Mapping):
        return {key: bool(explicit.get(key)) for key in _REQUIRED_STAGE_KEYS}
    # A valid pipeline closeout packet created by the closeout boundary implies
    # full stage coverage unless it says otherwise through missing_stages.
    missing = {str(item) for item in pipeline_closeout.get("missing_stages", []) or []}
    return {key: key not in missing for key in _REQUIRED_STAGE_KEYS}


def _artifact_quality_summary(files: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    roles = sorted({str(item.get("role", "")) for item in files if item.get("role")})
    missing_hashes = [str(item.get("filename", "")) for item in files if not _SHA256_RE.match(str(item.get("sha256", "")))]
    unsafe_names = [str(item.get("filename", "")) for item in files if not _SAFE_NAME_RE.match(str(item.get("filename", "")))]
    zero_byte_files = [str(item.get("filename", "")) for item in files if int(item.get("byte_count", 0) or 0) <= 0]
    return {
        "artifact_count": len(files),
        "artifact_roles": roles,
        "missing_or_invalid_hashes": missing_hashes,
        "unsafe_filenames": unsafe_names,
        "zero_byte_files": zero_byte_files,
        "artifact_quality_passed": not (missing_hashes or unsafe_names or zero_byte_files),
    }


def build_msn_manual_release_audit_report(
    release_pipeline_closeout_report: Mapping[str, Any] | str,
    *,
    store_reports: Sequence[Mapping[str, Any] | str] | None = None,
    operator_label: str = "manual_operator",
    audit_notes: str = "",
) -> dict[str, Any]:
    pipeline_closeout = _as_mapping(release_pipeline_closeout_report)
    receipts = [_as_mapping(item) for item in (store_reports or [])]

    queue_item_id = str(pipeline_closeout.get("queue_item_id") or "")
    release_id = str(pipeline_closeout.get("release_id") or "")
    pipeline_closeout_id = str(pipeline_closeout.get("pipeline_closeout_id") or "")
    closeout_schema = str(pipeline_closeout.get("schema_version") or "")
    pipeline_status = str(pipeline_closeout.get("pipeline_status") or "")

    stage_coverage = _stage_coverage(pipeline_closeout)
    missing_stages = [key for key, covered in stage_coverage.items() if not covered]
    transition_map = dict(pipeline_closeout.get("transition_map") or {})
    stored_files = _collect_stored_files(pipeline_closeout, *receipts)
    artifact_quality = _artifact_quality_summary(stored_files)

    readiness_issues: list[str] = []
    if closeout_schema != "msn_manual_release_pipeline_closeout_v1":
        readiness_issues.append("unexpected_pipeline_closeout_schema")
    if pipeline_status != "MSN_MANUAL_RELEASE_PIPELINE_CLOSED":
        readiness_issues.append("pipeline_not_closed")
    if not queue_item_id:
        readiness_issues.append("missing_queue_item_id")
    if not release_id:
        readiness_issues.append("missing_release_id")
    if not pipeline_closeout_id:
        readiness_issues.append("missing_pipeline_closeout_id")
    if missing_stages:
        readiness_issues.append("missing_stage_coverage")
    if transition_map.get("to_status") != "TOTAL_EXPORT_RELEASE_READY_FOR_OPERATOR_ARCHIVAL":
        readiness_issues.append("unexpected_transition_target")
    if not artifact_quality["artifact_quality_passed"]:
        readiness_issues.append("artifact_quality_failed")

    packet = {
        "schema_version": SCHEMA_VERSION,
        "audit_status": AUDIT_STATUS_READY if not readiness_issues else AUDIT_STATUS_REVIEW_REQUIRED,
        "queue_item_id": queue_item_id,
        "release_id": release_id,
        "pipeline_closeout_id": pipeline_closeout_id,
        "operator_label": _safe_text(operator_label, max_length=120),
        "audit_notes": _safe_text(audit_notes, max_length=500),
        "source_pipeline": {
            "schema_version": closeout_schema,
            "pipeline_status": pipeline_status,
            "content_sha256": str(pipeline_closeout.get("content_sha256") or ""),
        },
        "stage_coverage": stage_coverage,
        "stage_count": len(stage_coverage),
        "missing_stages": missing_stages,
        "readiness_issues": readiness_issues,
        "transition_map": transition_map,
        "artifact_ledger": stored_files,
        "artifact_quality": artifact_quality,
        "store_receipt_count": len(receipts),
        "store_receipt_schemas": sorted({str(item.get("schema_version") or "") for item in receipts if item.get("schema_version")}),
        "release_claims": [
            "MSN capture artifacts were supplied through explicit local operator files.",
            "The package is ready for Total Export handoff only after review approval and local release closeout.",
            "External archive URLs must be recorded separately after operator review.",
        ],
        "operator_constraints": [
            "Do not run live capture or archive submission from this audit boundary.",
            "Do not read key material or provider auth material.",
            "Do not claim independent verification of external content from this local audit packet alone.",
            "Use only safe relative filenames in release artifacts.",
        ],
    }
    packet["audit_report_id"] = f"{release_id or queue_item_id}.audit.{_hash_json(packet)[:12]}"
    packet["content_sha256"] = _hash_json(packet)
    return packet


def msn_manual_release_audit_report_to_json(packet: Mapping[str, Any]) -> str:
    return _stable_json(packet) + "\n"


def inspect_msn_manual_release_audit_report_safety(packet: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    for value in _nested_values(packet):
        text = str(value)
        if _SECRET_FIELD_RE.search(text):
            issues.append(f"secret_like_value:{text[:64]}")
        if _ABSOLUTE_PATH_RE.search(text):
            issues.append(f"absolute_path_like_value:{text[:64]}")

    for item in packet.get("artifact_ledger", []) or []:
        filename = str(item.get("filename", ""))
        if filename and not _SAFE_NAME_RE.match(filename):
            issues.append(f"unsafe_filename:{filename}")

    return {
        "safe": not issues,
        "issues": issues,
        "issue_count": len(issues),
    }


if __name__ == "__main__":
    sample = build_msn_manual_release_audit_report(
        {
            "schema_version": "msn_manual_release_pipeline_closeout_v1",
            "pipeline_status": "MSN_MANUAL_RELEASE_PIPELINE_CLOSED",
            "queue_item_id": "msn.queue",
            "release_id": "msn.queue.release.1234",
            "pipeline_closeout_id": "msn.queue.release.1234.pipeline_closeout.abc123",
            "transition_map": {"to_status": "TOTAL_EXPORT_RELEASE_READY_FOR_OPERATOR_ARCHIVAL"},
            "stage_coverage": {key: True for key in _REQUIRED_STAGE_KEYS},
            "stored_files": [
                {
                    "filename": "msn.queue.release.1234.pipeline_closeout.abc123.release_pipeline_closeout.json",
                    "role": "msn_manual_release_pipeline_closeout",
                    "sha256": "0" * 64,
                    "byte_count": 100,
                }
            ],
        }
    )
    assert sample["audit_status"] == AUDIT_STATUS_READY
    assert inspect_msn_manual_release_audit_report_safety(sample)["safe"]
    print("MSN manual release audit report self-test passed.")
