from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping

from source_release_index import build_source_release_index

SCHEMA_VERSION = "source_adapter_release_index_bridge_v1"
RELEASE_INDEX_BATCH_SCHEMA_VERSION = "source_adapter_release_index_batch_v1"
RELEASE_AUDIT_HANDOFF_SCHEMA_VERSION = "source_adapter_release_audit_batch_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_release_index_bridge_operator_summary_v1"
RELEASE_INDEX_BRIDGE_STATUS = "SHARED_RELEASE_INDEXES_BUILT"
RELEASE_AUDIT_HANDOFF_STATUS = "READY_FOR_SHARED_RELEASE_AUDIT"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _stable_hash(value: Any, *, length: int = 12) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()[:length]


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return value


def _as_mapping_list(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise TypeError(f"{label} must be a list")
    return [_as_mapping(item, f"{label} item") for item in value]


def _safe_text(value: Any, default: str = "") -> str:
    return str(value if value is not None else default).replace("\r", " ").strip()


def _safe_id(value: Any, *, label: str, fallback: str = "") -> str:
    text = _safe_text(value, fallback)
    if not text:
        raise ValueError(f"{label} is required")
    if not _SAFE_ID_RE.match(text):
        raise ValueError(f"{label} must contain only letters, numbers, dot, underscore, or dash")
    return text


def _normalise_notes(notes: Iterable[str] | None) -> list[str]:
    return [str(note).strip() for note in (notes or []) if str(note).strip()]


def _approved_outputs(approved_release_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _as_mapping_list(approved_release_bridge_package.get("approved_release_outputs"), "approved_release_outputs")


def _approved_output_parts(output: Mapping[str, Any], index: int) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    package = _as_mapping(output.get("approved_release_package"), f"approved_release_outputs[{index}].approved_release_package")
    manifest = _as_mapping(output.get("approved_release_manifest"), f"approved_release_outputs[{index}].approved_release_manifest")
    handoff = _as_mapping(output.get("release_index_handoff"), f"approved_release_outputs[{index}].release_index_handoff")
    return package, manifest, handoff


def _row_from_outputs(outputs: Mapping[str, Any]) -> dict[str, Any]:
    record = _as_mapping(outputs.get("release_index_record"), "release_index_record")
    inventory = _as_mapping(outputs.get("release_inventory"), "release_inventory")
    handoff = _as_mapping(outputs.get("export_bundle_handoff"), "export_bundle_handoff")
    release_index_id = _safe_id(record.get("release_index_id"), label="release_index_id")
    return {
        "adapter_id": _safe_text(record.get("adapter_id"), ""),
        "source_url": _safe_text(record.get("source_url"), ""),
        "queue_item_id": _safe_text(record.get("queue_item_id"), ""),
        "total_export_package_id": _safe_text(record.get("total_export_package_id"), ""),
        "capture_bundle_id": _safe_text(record.get("capture_bundle_id"), ""),
        "evidence_review_package_id": _safe_text(record.get("evidence_review_package_id"), ""),
        "approved_release_id": _safe_text(record.get("approved_release_id"), ""),
        "release_index_id": release_index_id,
        "release_index_status": record.get("release_index_status", ""),
        "inventory_status": inventory.get("inventory_status", ""),
        "artifact_count": record.get("artifact_count", 0),
        "artifact_roles": list(record.get("artifact_roles", [])) if isinstance(record.get("artifact_roles"), list) else [],
        "handoff_status": handoff.get("handoff_status", ""),
        "required_next_stage": handoff.get("required_next_stage", ""),
        "index_fingerprint": record.get("index_fingerprint", ""),
    }


def build_source_adapter_release_index_bridge(
    approved_release_bridge_package: Mapping[str, Any],
    *,
    indexer_id: str = "manual_indexer",
    release_index_profile: str = "source_adapter_shared_release_index_v1",
    release_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build shared Release Index outputs from Adapter Approved Release Bridge output."""

    package = _as_mapping(approved_release_bridge_package, "approved_release_bridge_package")
    if package.get("approved_release_bridge_status") != "SHARED_APPROVED_RELEASES_BUILT":
        raise ValueError("approved release bridge package must be SHARED_APPROVED_RELEASES_BUILT")
    handoff = package.get("source_adapter_release_index_batch_handoff")
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != "READY_FOR_SHARED_RELEASE_INDEX":
        raise ValueError("approved release bridge handoff must be READY_FOR_SHARED_RELEASE_INDEX")
    if handoff.get("ready_for_release_index") is not True:
        raise ValueError("approved release bridge handoff must be ready_for_release_index")

    notes = _normalise_notes(release_notes)
    approved_outputs = _approved_outputs(package)
    if not approved_outputs:
        raise ValueError("at least one Approved Release output is required")

    release_index_outputs: list[dict[str, Any]] = []
    release_index_rows: list[dict[str, Any]] = []
    issue_rows: list[str] = []
    seen_release_index_ids: set[str] = set()

    for index, output in enumerate(approved_outputs):
        approved_release_package, approved_release_manifest, release_index_handoff = _approved_output_parts(output, index)
        approved_release_id = _safe_id(approved_release_package.get("approved_release_id"), label="approved_release_id", fallback=f"approved_release_{index}")
        try:
            outputs = build_source_release_index(
                approved_release_package=approved_release_package,
                approved_release_manifest=approved_release_manifest,
                release_index_handoff=release_index_handoff,
                indexer_id=indexer_id,
                release_index_profile=release_index_profile,
                release_notes=notes,
            ).as_dict()
            row = _row_from_outputs(outputs)
        except Exception as exc:  # deterministic batch issue capture for operator review
            issue_rows.append(f"{approved_release_id}: {exc}")
            continue
        if row["release_index_id"] in seen_release_index_ids:
            issue_rows.append(f"duplicate release index id: {row['release_index_id']}")
            continue
        seen_release_index_ids.add(row["release_index_id"])
        release_index_outputs.append(dict(outputs))
        release_index_rows.append(row)

    built = bool(release_index_outputs) and not issue_rows
    release_index_batch = {
        "schema_version": RELEASE_INDEX_BATCH_SCHEMA_VERSION,
        "release_index_count": len(release_index_outputs),
        "release_index_rows": release_index_rows,
        "release_index_profile": release_index_profile,
    }
    release_audit_handoff = {
        "schema_version": RELEASE_AUDIT_HANDOFF_SCHEMA_VERSION,
        "handoff_status": RELEASE_AUDIT_HANDOFF_STATUS if built else "RELEASE_INDEX_BRIDGE_BLOCKED",
        "ready_for_release_audit": built,
        "required_next_stage": "source_release_audit",
        "release_index_ids": [row["release_index_id"] for row in release_index_rows],
        "release_audit_inputs": [
            {
                "role": "source_release_index_record",
                "id": row["release_index_id"],
                "filename_hint": f"{row['release_index_id']}.source_release_index_record.json",
            }
            for row in release_index_rows
        ],
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": RELEASE_INDEX_BRIDGE_STATUS if built else "RELEASE_INDEX_BRIDGE_BLOCKED",
        "release_index_count": len(release_index_outputs),
        "issue_count": len(issue_rows),
        "release_index_profile": release_index_profile,
        "release_notes": notes,
        "implemented_stage": "source_release_index",
        "next_actions": [
            "Pass release-index outputs and release-audit handoffs to the source_release_audit stage.",
            "Keep Approved Release packages and Evidence Review decisions immutable.",
            "Use this shared release-index bridge for future adapters unless a source has a genuinely unique index-shape requirement.",
        ],
    }
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "release_index_bridge_status": RELEASE_INDEX_BRIDGE_STATUS if built else "RELEASE_INDEX_BRIDGE_BLOCKED",
        "source_adapter_approved_release_bridge_id": _safe_text(package.get("source_adapter_approved_release_bridge_id"), ""),
        "release_index_count": len(release_index_outputs),
        "issue_count": len(issue_rows),
        "issues": issue_rows,
        "release_index_outputs": release_index_outputs,
        "source_adapter_release_index_batch": release_index_batch,
        "source_adapter_release_audit_batch_handoff": release_audit_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "shared_stage_executed": "source_release_index",
            "input_source": "source_adapter_approved_release_bridge",
            "per_adapter_path": "approved_release_output_plus_shared_release_index_builder",
            "multi_adapter_batch_supported": True,
        },
    }
    bridge_id = f"source_adapter_release_index_bridge.{_stable_hash(unsigned)}"
    result = dict(unsigned)
    result["source_adapter_release_index_bridge_id"] = bridge_id
    result["source_adapter_release_index_batch"] = dict(release_index_batch, source_adapter_release_index_bridge_id=bridge_id)
    result["source_adapter_release_audit_batch_handoff"] = dict(release_audit_handoff, source_adapter_release_index_bridge_id=bridge_id)
    result["operator_summary"] = dict(operator_summary, source_adapter_release_index_bridge_id=bridge_id)
    return result


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_release_index_bridge_package": dict(pkg),
        "source_adapter_release_index_output_batch": deepcopy(pkg.get("release_index_outputs", [])),
        "source_adapter_release_index_batch": deepcopy(pkg.get("source_adapter_release_index_batch", {})),
        "source_adapter_release_audit_batch_handoff": deepcopy(pkg.get("source_adapter_release_audit_batch_handoff", {})),
        "source_adapter_release_index_bridge_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    from source_adapter_approved_release_bridge import build_source_adapter_approved_release_bridge
    from source_adapter_approved_release_bridge_test import fixture_evidence_review_bridge

    approved_bridge = build_source_adapter_approved_release_bridge(fixture_evidence_review_bridge())
    result = build_source_adapter_release_index_bridge(approved_bridge)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
