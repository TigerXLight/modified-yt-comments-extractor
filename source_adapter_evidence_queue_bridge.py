from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping

from source_evidence_queue import build_source_evidence_queue

SCHEMA_VERSION = "source_adapter_evidence_queue_bridge_v1"
QUEUE_BATCH_SCHEMA_VERSION = "source_adapter_evidence_queue_batch_v1"
REVIEW_HANDOFF_SCHEMA_VERSION = "source_adapter_evidence_review_batch_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_evidence_queue_bridge_operator_summary_v1"
EVIDENCE_QUEUE_BRIDGE_STATUS = "SHARED_EVIDENCE_QUEUE_ITEMS_BUILT"
EVIDENCE_REVIEW_HANDOFF_STATUS = "READY_FOR_SHARED_EVIDENCE_REVIEW"

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


def _total_export_outputs(total_export_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _as_mapping_list(total_export_bridge_package.get("total_export_outputs"), "total_export_outputs")


def _output_package(output: Mapping[str, Any], index: int) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    package = _as_mapping(output.get("total_export_package"), f"total_export_outputs[{index}].total_export_package")
    manifest = _as_mapping(output.get("total_export_manifest"), f"total_export_outputs[{index}].total_export_manifest")
    handoff = _as_mapping(output.get("evidence_queue_handoff"), f"total_export_outputs[{index}].evidence_queue_handoff")
    return package, manifest, handoff


def _row_from_outputs(outputs: Mapping[str, Any]) -> dict[str, Any]:
    item = _as_mapping(outputs.get("evidence_queue_item"), "evidence_queue_item")
    index = _as_mapping(outputs.get("evidence_queue_index"), "evidence_queue_index")
    handoff = _as_mapping(outputs.get("evidence_review_handoff"), "evidence_review_handoff")
    queue_item_id = _safe_id(item.get("queue_item_id"), label="queue_item_id")
    return {
        "adapter_id": _safe_text(item.get("adapter_id"), ""),
        "source_url": _safe_text(item.get("source_url"), ""),
        "total_export_package_id": _safe_text(item.get("total_export_package_id"), ""),
        "capture_bundle_id": _safe_text(item.get("capture_bundle_id"), ""),
        "queue_item_id": queue_item_id,
        "queue_status": item.get("queue_status", ""),
        "review_state": item.get("review_state", ""),
        "artifact_count": item.get("artifact_count", 0),
        "comment_count": item.get("comment_summary", {}).get("comment_count", 0) if isinstance(item.get("comment_summary"), Mapping) else 0,
        "index_status": index.get("items", [{}])[0].get("queue_status", "") if isinstance(index.get("items"), list) and index.get("items") else "",
        "handoff_status": handoff.get("handoff_status", ""),
    }


def build_source_adapter_evidence_queue_bridge(
    total_export_bridge_package: Mapping[str, Any],
    *,
    queue_profile: str = "source_adapter_shared_v1",
    queue_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build shared Evidence Queue items from Adapter Total Export Bridge output."""

    package = _as_mapping(total_export_bridge_package, "total_export_bridge_package")
    if package.get("total_export_bridge_status") != "SHARED_TOTAL_EXPORT_PACKAGES_BUILT":
        raise ValueError("total export bridge package must be SHARED_TOTAL_EXPORT_PACKAGES_BUILT")
    handoff = package.get("source_adapter_evidence_queue_handoff")
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != "READY_FOR_SHARED_EVIDENCE_QUEUE":
        raise ValueError("total export bridge handoff must be READY_FOR_SHARED_EVIDENCE_QUEUE")

    notes = _normalise_notes(queue_notes)
    total_export_outputs = _total_export_outputs(package)
    if not total_export_outputs:
        raise ValueError("at least one Total Export output is required")

    queue_outputs: list[dict[str, Any]] = []
    queue_rows: list[dict[str, Any]] = []
    issue_rows: list[str] = []
    seen_queue_ids: set[str] = set()

    for index, output in enumerate(total_export_outputs):
        total_export_package, total_export_manifest, evidence_queue_handoff = _output_package(output, index)
        try:
            package_id = _safe_id(total_export_package.get("total_export_package_id"), label="total_export_package_id")
            if total_export_manifest.get("total_export_package_id") != package_id:
                raise ValueError("total_export_manifest total_export_package_id mismatch")
            outputs = build_source_evidence_queue(
                total_export_package=total_export_package,
                evidence_queue_handoff=evidence_queue_handoff,
                queue_profile=queue_profile,
                queue_notes=notes,
            ).as_dict()
            row = _row_from_outputs(outputs)
        except Exception as exc:  # deterministic batch issue capture for operator review
            package_id = _safe_text(total_export_package.get("total_export_package_id"), f"total_export_package_{index}") if isinstance(total_export_package, Mapping) else f"total_export_package_{index}"
            issue_rows.append(f"{package_id}: {exc}")
            continue
        if row["queue_item_id"] in seen_queue_ids:
            issue_rows.append(f"duplicate evidence queue item id: {row['queue_item_id']}")
            continue
        seen_queue_ids.add(row["queue_item_id"])
        queue_outputs.append(dict(outputs))
        queue_rows.append(row)

    ready = bool(queue_outputs) and not issue_rows
    queue_batch = {
        "schema_version": QUEUE_BATCH_SCHEMA_VERSION,
        "queue_item_count": len(queue_outputs),
        "ready_for_review_count": sum(1 for row in queue_rows if row["queue_status"] == "READY_FOR_EVIDENCE_REVIEW"),
        "queue_rows": queue_rows,
    }
    evidence_review_handoff = {
        "schema_version": REVIEW_HANDOFF_SCHEMA_VERSION,
        "handoff_status": EVIDENCE_REVIEW_HANDOFF_STATUS if ready else "EVIDENCE_QUEUE_BRIDGE_BLOCKED",
        "ready_for_evidence_review": ready,
        "required_next_stage": "source_evidence_review",
        "queue_item_ids": [row["queue_item_id"] for row in queue_rows],
        "review_inputs": [
            {
                "role": "source_evidence_queue_item",
                "id": row["queue_item_id"],
                "filename_hint": f"{row['queue_item_id']}.source_evidence_queue_item.json",
            }
            for row in queue_rows
        ],
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": EVIDENCE_QUEUE_BRIDGE_STATUS if ready else "EVIDENCE_QUEUE_BRIDGE_BLOCKED",
        "queue_item_count": len(queue_outputs),
        "issue_count": len(issue_rows),
        "queue_profile": queue_profile,
        "queue_notes": notes,
        "implemented_stage": "source_evidence_queue",
        "next_actions": [
            "Pass the Evidence Queue batch and shared review handoff to the source_evidence_review stage.",
            "Reviewers can approve, reject, or request revision without changing upstream packages.",
            "Keep adapter-specific code limited to genuinely different evidence identity or review-shape requirements.",
        ],
    }
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "evidence_queue_bridge_status": EVIDENCE_QUEUE_BRIDGE_STATUS if ready else "EVIDENCE_QUEUE_BRIDGE_BLOCKED",
        "source_adapter_total_export_bridge_id": _safe_text(package.get("source_adapter_total_export_bridge_id"), ""),
        "queue_item_count": len(queue_outputs),
        "issue_count": len(issue_rows),
        "issues": issue_rows,
        "evidence_queue_outputs": queue_outputs,
        "source_adapter_evidence_queue_batch": queue_batch,
        "source_adapter_evidence_review_batch_handoff": evidence_review_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "shared_stage_executed": "source_evidence_queue",
            "input_source": "source_adapter_total_export_bridge",
            "per_adapter_path": "total_export_package_plus_shared_evidence_queue_builder",
            "multi_adapter_batch_supported": True,
        },
    }
    bridge_id = f"source_adapter_evidence_queue_bridge.{_stable_hash(unsigned)}"
    result = dict(unsigned)
    result["source_adapter_evidence_queue_bridge_id"] = bridge_id
    result["source_adapter_evidence_queue_batch"] = dict(queue_batch, source_adapter_evidence_queue_bridge_id=bridge_id)
    result["source_adapter_evidence_review_batch_handoff"] = dict(evidence_review_handoff, source_adapter_evidence_queue_bridge_id=bridge_id)
    result["operator_summary"] = dict(operator_summary, source_adapter_evidence_queue_bridge_id=bridge_id)
    return result


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_evidence_queue_bridge_package": dict(pkg),
        "source_adapter_evidence_queue_item_batch": deepcopy(pkg.get("evidence_queue_outputs", [])),
        "source_adapter_evidence_queue_batch": deepcopy(pkg.get("source_adapter_evidence_queue_batch", {})),
        "source_adapter_evidence_review_batch_handoff": deepcopy(pkg.get("source_adapter_evidence_review_batch_handoff", {})),
        "source_adapter_evidence_queue_bridge_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    from source_adapter_total_export_bridge import build_source_adapter_total_export_bridge
    from source_adapter_total_export_bridge_test import fixture_capture_bundle_bridge

    bridge_input = build_source_adapter_total_export_bridge(fixture_capture_bundle_bridge())
    result = build_source_adapter_evidence_queue_bridge(bridge_input)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
