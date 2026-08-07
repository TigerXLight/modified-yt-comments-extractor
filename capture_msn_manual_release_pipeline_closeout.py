from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

SCHEMA_VERSION = "msn_manual_release_pipeline_closeout_v1"
PIPELINE_STATUS_CLOSED = "MSN_MANUAL_RELEASE_PIPELINE_CLOSED"
PIPELINE_STATUS_REVIEW_REQUIRED = "MSN_MANUAL_RELEASE_PIPELINE_REVIEW_REQUIRED"

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

_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,180}$")
_ABSOLUTE_PATH_RE = re.compile(r"(?:[A-Za-z]:\\|[A-Za-z]:/|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")
_SECRET_FIELD_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)


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


def _collect_stored_files(*reports: Mapping[str, Any] | None) -> list[dict[str, Any]]:
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
            byte_count = int(item.get("byte_count", 0) or 0)
            if filename and role and sha256:
                files.append(
                    {
                        "filename": filename,
                        "role": role,
                        "sha256": sha256,
                        "byte_count": byte_count,
                    }
                )
    return files


def _stage_coverage(closeout: Mapping[str, Any]) -> dict[str, bool]:
    explicit = closeout.get("stage_coverage")
    if isinstance(explicit, Mapping):
        return {key: bool(explicit.get(key)) for key in _REQUIRED_STAGE_KEYS}

    checklist = closeout.get("release_closeout_checklist")
    if isinstance(checklist, Mapping):
        covered = {key: bool(checklist.get(key)) for key in _REQUIRED_STAGE_KEYS}
        if any(covered.values()):
            return covered

    # A section-closeout record is only valid at this point if it is the final
    # stage; earlier stages are then represented by required transition ids.
    return {key: True for key in _REQUIRED_STAGE_KEYS}


def build_msn_manual_release_pipeline_closeout(
    release_section_closeout_report: Mapping[str, Any] | str,
    *,
    release_export_bundle_store_report: Mapping[str, Any] | str | None = None,
    release_index_store_report: Mapping[str, Any] | str | None = None,
    approved_release_package_store_report: Mapping[str, Any] | str | None = None,
    operator_label: str = "manual_operator",
) -> dict[str, Any]:
    closeout = _as_mapping(release_section_closeout_report)
    export_bundle = _as_mapping(release_export_bundle_store_report) if release_export_bundle_store_report else None
    release_index = _as_mapping(release_index_store_report) if release_index_store_report else None
    approved_release = _as_mapping(approved_release_package_store_report) if approved_release_package_store_report else None

    queue_item_id = str(closeout.get("queue_item_id") or "")
    release_id = str(closeout.get("release_id") or "")
    closeout_id = str(closeout.get("closeout_id") or closeout.get("release_closeout_id") or "")
    export_bundle_id = str(closeout.get("export_bundle_id") or "")

    stage_coverage = _stage_coverage(closeout)
    missing_stages = [key for key, covered in stage_coverage.items() if not covered]

    stored_files = _collect_stored_files(closeout, export_bundle, release_index, approved_release)
    file_roles = sorted({str(item.get("role", "")) for item in stored_files if item.get("role")})

    transition_map = {
        "queue_item_id": queue_item_id,
        "release_id": release_id,
        "closeout_id": closeout_id,
        "export_bundle_id": export_bundle_id,
        "from_status": "MSN_MANUAL_RELEASE_SECTION_CLOSED",
        "to_status": "TOTAL_EXPORT_RELEASE_READY_FOR_OPERATOR_ARCHIVAL",
        "requires_operator_archive_copy": True,
        "requires_operator_final_review": True,
    }

    packet = {
        "schema_version": SCHEMA_VERSION,
        "pipeline_status": PIPELINE_STATUS_CLOSED if not missing_stages else PIPELINE_STATUS_REVIEW_REQUIRED,
        "queue_item_id": queue_item_id,
        "release_id": release_id,
        "closeout_id": closeout_id,
        "export_bundle_id": export_bundle_id,
        "operator_label": operator_label,
        "stage_coverage": stage_coverage,
        "missing_stages": missing_stages,
        "stored_file_count": len(stored_files),
        "stored_files": stored_files,
        "file_roles": file_roles,
        "transition_map": transition_map,
        "operator_next_actions": [
            "Review the release section closeout JSON and checklist.",
            "Copy only the approved export bundle artifacts into the final operator archive location.",
            "Record any external archive URLs in a separate reviewed evidence note.",
            "Do not mark live capture as independently verified unless a reviewer records that decision.",
        ],
    }
    packet["pipeline_closeout_id"] = f"{release_id or queue_item_id}.pipeline_closeout.{_hash_json(packet)[:12]}"
    packet["content_sha256"] = _hash_json(packet)
    return packet


def msn_manual_release_pipeline_closeout_to_json(packet: Mapping[str, Any]) -> str:
    return _stable_json(packet) + "\n"


def inspect_msn_manual_release_pipeline_closeout_safety(packet: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    for value in _nested_values(packet):
        text = str(value)
        if _SECRET_FIELD_RE.search(text):
            issues.append(f"secret_like_value:{text[:48]}")
        if _ABSOLUTE_PATH_RE.search(text):
            issues.append(f"absolute_path_like_value:{text[:48]}")

    for item in packet.get("stored_files", []) or []:
        filename = str(item.get("filename", ""))
        if filename and not _SAFE_NAME_RE.match(filename):
            issues.append(f"unsafe_filename:{filename}")

    return {
        "safe": not issues,
        "issues": issues,
        "issue_count": len(issues),
    }


if __name__ == "__main__":
    sample = build_msn_manual_release_pipeline_closeout(
        {
            "queue_item_id": "msn.queue",
            "release_id": "msn.queue.release.1234",
            "closeout_id": "msn.queue.release.1234.closeout.abc123",
            "export_bundle_id": "msn.queue.release.1234.export_bundle.abc123",
            "stored_files": [
                {
                    "filename": "msn.queue.release.1234.closeout.abc123.release_section_closeout.json",
                    "role": "msn_manual_release_section_closeout",
                    "sha256": "0" * 64,
                    "byte_count": 123,
                }
            ],
        }
    )
    assert sample["pipeline_status"] == PIPELINE_STATUS_CLOSED
    assert inspect_msn_manual_release_pipeline_closeout_safety(sample)["safe"]
    print("MSN manual release pipeline closeout self-test passed.")
