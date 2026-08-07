from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping

from source_evidence_review import build_source_evidence_review

SCHEMA_VERSION = "source_adapter_evidence_review_bridge_v1"
REVIEW_BATCH_SCHEMA_VERSION = "source_adapter_evidence_review_batch_v1"
APPROVED_HANDOFF_SCHEMA_VERSION = "source_adapter_approved_release_batch_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_evidence_review_bridge_operator_summary_v1"
EVIDENCE_REVIEW_BRIDGE_STATUS = "SHARED_EVIDENCE_REVIEWS_BUILT"
APPROVED_RELEASE_HANDOFF_STATUS = "READY_FOR_SHARED_APPROVED_RELEASE"

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


def _normalise_decision(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {"decision": "PENDING_DECISION"}
    decision = dict(_as_mapping(value, "reviewer_decision"))
    if "decision" not in decision and "review_decision" in decision:
        decision["decision"] = decision["review_decision"]
    decision.setdefault("decision", "PENDING_DECISION")
    return decision


def _decision_for_item(reviewer_decision: Mapping[str, Any] | None, queue_item_id: str) -> dict[str, Any]:
    if reviewer_decision is None:
        return {"decision": "PENDING_DECISION"}
    decision_root = _as_mapping(reviewer_decision, "reviewer_decision")
    by_id = decision_root.get("decisions_by_queue_item_id")
    if isinstance(by_id, Mapping) and isinstance(by_id.get(queue_item_id), Mapping):
        return _normalise_decision(by_id[queue_item_id])
    per_item = decision_root.get("per_queue_item_decisions")
    if isinstance(per_item, list):
        for item in per_item:
            if isinstance(item, Mapping) and str(item.get("queue_item_id") or "") == queue_item_id:
                return _normalise_decision(item)
    shared = {key: value for key, value in decision_root.items() if key not in {"decisions_by_queue_item_id", "per_queue_item_decisions"}}
    return _normalise_decision(shared)


def _queue_outputs(evidence_queue_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _as_mapping_list(evidence_queue_bridge_package.get("evidence_queue_outputs"), "evidence_queue_outputs")


def _output_item(output: Mapping[str, Any], index: int) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    item = _as_mapping(output.get("evidence_queue_item"), f"evidence_queue_outputs[{index}].evidence_queue_item")
    handoff = _as_mapping(output.get("evidence_review_handoff"), f"evidence_queue_outputs[{index}].evidence_review_handoff")
    return item, handoff


def _row_from_outputs(outputs: Mapping[str, Any]) -> dict[str, Any]:
    package = _as_mapping(outputs.get("evidence_review_package"), "evidence_review_package")
    decision = _as_mapping(outputs.get("evidence_review_decision"), "evidence_review_decision")
    handoff = _as_mapping(outputs.get("release_handoff"), "release_handoff")
    review_package_id = _safe_id(package.get("evidence_review_package_id"), label="evidence_review_package_id")
    return {
        "adapter_id": _safe_text(package.get("adapter_id"), ""),
        "source_url": _safe_text(package.get("source_url"), ""),
        "queue_item_id": _safe_text(package.get("queue_item_id"), ""),
        "total_export_package_id": _safe_text(package.get("total_export_package_id"), ""),
        "capture_bundle_id": _safe_text(package.get("capture_bundle_id"), ""),
        "evidence_review_package_id": review_package_id,
        "review_package_status": package.get("review_package_status", ""),
        "decision": decision.get("decision", ""),
        "review_status": decision.get("review_status", ""),
        "approved_for_release": bool(decision.get("approved_for_release")),
        "handoff_status": handoff.get("handoff_status", ""),
        "required_next_stage": handoff.get("required_next_stage", ""),
    }


def build_source_adapter_evidence_review_bridge(
    evidence_queue_bridge_package: Mapping[str, Any],
    *,
    reviewer_decision: Mapping[str, Any] | None = None,
    reviewer_id: str = "manual_reviewer",
    review_profile: str = "source_adapter_shared_review_v1",
    review_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build shared Evidence Review outputs from Adapter Evidence Queue Bridge output."""

    package = _as_mapping(evidence_queue_bridge_package, "evidence_queue_bridge_package")
    if package.get("evidence_queue_bridge_status") != "SHARED_EVIDENCE_QUEUE_ITEMS_BUILT":
        raise ValueError("evidence queue bridge package must be SHARED_EVIDENCE_QUEUE_ITEMS_BUILT")
    handoff = package.get("source_adapter_evidence_review_batch_handoff")
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != "READY_FOR_SHARED_EVIDENCE_REVIEW":
        raise ValueError("evidence queue bridge handoff must be READY_FOR_SHARED_EVIDENCE_REVIEW")

    notes = _normalise_notes(review_notes)
    queue_outputs = _queue_outputs(package)
    if not queue_outputs:
        raise ValueError("at least one Evidence Queue output is required")

    review_outputs: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    issue_rows: list[str] = []
    seen_review_ids: set[str] = set()

    for index, output in enumerate(queue_outputs):
        queue_item, evidence_review_handoff = _output_item(output, index)
        queue_item_id = _safe_id(queue_item.get("queue_item_id"), label="queue_item_id", fallback=f"queue_item_{index}")
        try:
            decision = _decision_for_item(reviewer_decision, queue_item_id)
            outputs = build_source_evidence_review(
                evidence_queue_item=queue_item,
                evidence_review_handoff=evidence_review_handoff,
                reviewer_decision=decision,
                reviewer_id=reviewer_id,
                review_profile=review_profile,
                review_notes=notes,
            ).as_dict()
            row = _row_from_outputs(outputs)
        except Exception as exc:  # deterministic batch issue capture for operator review
            issue_rows.append(f"{queue_item_id}: {exc}")
            continue
        if row["evidence_review_package_id"] in seen_review_ids:
            issue_rows.append(f"duplicate evidence review package id: {row['evidence_review_package_id']}")
            continue
        seen_review_ids.add(row["evidence_review_package_id"])
        review_outputs.append(dict(outputs))
        review_rows.append(row)

    built = bool(review_outputs) and not issue_rows
    approved_count = sum(1 for row in review_rows if row["approved_for_release"])
    pending_count = sum(1 for row in review_rows if row["decision"] == "PENDING_DECISION")
    revision_count = sum(1 for row in review_rows if row["decision"] == "REVISION_REQUESTED")
    rejected_count = sum(1 for row in review_rows if row["decision"] == "REJECTED")
    ready_for_release = built and approved_count == len(review_rows) and bool(review_rows)

    review_batch = {
        "schema_version": REVIEW_BATCH_SCHEMA_VERSION,
        "evidence_review_count": len(review_outputs),
        "approved_for_release_count": approved_count,
        "pending_decision_count": pending_count,
        "revision_requested_count": revision_count,
        "rejected_count": rejected_count,
        "review_rows": review_rows,
    }
    approved_release_handoff = {
        "schema_version": APPROVED_HANDOFF_SCHEMA_VERSION,
        "handoff_status": APPROVED_RELEASE_HANDOFF_STATUS if ready_for_release else "EVIDENCE_REVIEW_BRIDGE_PENDING_OR_BLOCKED",
        "ready_for_approved_release": ready_for_release,
        "required_next_stage": "source_approved_release",
        "evidence_review_package_ids": [row["evidence_review_package_id"] for row in review_rows],
        "approved_release_inputs": [
            {
                "role": "source_evidence_review_package",
                "id": row["evidence_review_package_id"],
                "filename_hint": f"{row['evidence_review_package_id']}.source_evidence_review_package.json",
            }
            for row in review_rows
            if row["approved_for_release"]
        ],
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": EVIDENCE_REVIEW_BRIDGE_STATUS if built else "EVIDENCE_REVIEW_BRIDGE_BLOCKED",
        "evidence_review_count": len(review_outputs),
        "approved_for_release_count": approved_count,
        "pending_decision_count": pending_count,
        "revision_requested_count": revision_count,
        "rejected_count": rejected_count,
        "issue_count": len(issue_rows),
        "review_profile": review_profile,
        "review_notes": notes,
        "implemented_stage": "source_evidence_review",
        "next_actions": [
            "Pass approved Evidence Review outputs and release handoffs to the source_approved_release stage.",
            "Use pending, rejected, or revision-requested decisions to keep review work explicit before release.",
            "Keep adapter-specific code limited to genuinely different review or release-shape requirements.",
        ],
    }
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "evidence_review_bridge_status": EVIDENCE_REVIEW_BRIDGE_STATUS if built else "EVIDENCE_REVIEW_BRIDGE_BLOCKED",
        "source_adapter_evidence_queue_bridge_id": _safe_text(package.get("source_adapter_evidence_queue_bridge_id"), ""),
        "evidence_review_count": len(review_outputs),
        "issue_count": len(issue_rows),
        "issues": issue_rows,
        "evidence_review_outputs": review_outputs,
        "source_adapter_evidence_review_batch": review_batch,
        "source_adapter_approved_release_batch_handoff": approved_release_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "shared_stage_executed": "source_evidence_review",
            "input_source": "source_adapter_evidence_queue_bridge",
            "per_adapter_path": "evidence_queue_item_plus_shared_evidence_review_builder",
            "multi_adapter_batch_supported": True,
        },
    }
    bridge_id = f"source_adapter_evidence_review_bridge.{_stable_hash(unsigned)}"
    result = dict(unsigned)
    result["source_adapter_evidence_review_bridge_id"] = bridge_id
    result["source_adapter_evidence_review_batch"] = dict(review_batch, source_adapter_evidence_review_bridge_id=bridge_id)
    result["source_adapter_approved_release_batch_handoff"] = dict(approved_release_handoff, source_adapter_evidence_review_bridge_id=bridge_id)
    result["operator_summary"] = dict(operator_summary, source_adapter_evidence_review_bridge_id=bridge_id)
    return result


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_evidence_review_bridge_package": dict(pkg),
        "source_adapter_evidence_review_output_batch": deepcopy(pkg.get("evidence_review_outputs", [])),
        "source_adapter_evidence_review_batch": deepcopy(pkg.get("source_adapter_evidence_review_batch", {})),
        "source_adapter_approved_release_batch_handoff": deepcopy(pkg.get("source_adapter_approved_release_batch_handoff", {})),
        "source_adapter_evidence_review_bridge_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    from source_adapter_evidence_queue_bridge import build_source_adapter_evidence_queue_bridge
    from source_adapter_evidence_queue_bridge_test import fixture_total_export_bridge

    queue_bridge = build_source_adapter_evidence_queue_bridge(fixture_total_export_bridge())
    result = build_source_adapter_evidence_review_bridge(queue_bridge, reviewer_decision={"decision": "APPROVED"})
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
