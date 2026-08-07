from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping

from source_approved_release import build_source_approved_release

SCHEMA_VERSION = "source_adapter_approved_release_bridge_v1"
APPROVED_RELEASE_BATCH_SCHEMA_VERSION = "source_adapter_approved_release_batch_v1"
RELEASE_INDEX_HANDOFF_SCHEMA_VERSION = "source_adapter_release_index_batch_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_approved_release_bridge_operator_summary_v1"
APPROVED_RELEASE_BRIDGE_STATUS = "SHARED_APPROVED_RELEASES_BUILT"
RELEASE_INDEX_HANDOFF_STATUS = "READY_FOR_SHARED_RELEASE_INDEX"

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


def _review_outputs(evidence_review_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _as_mapping_list(evidence_review_bridge_package.get("evidence_review_outputs"), "evidence_review_outputs")


def _review_output_parts(output: Mapping[str, Any], index: int) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    package = _as_mapping(output.get("evidence_review_package"), f"evidence_review_outputs[{index}].evidence_review_package")
    decision = _as_mapping(output.get("evidence_review_decision"), f"evidence_review_outputs[{index}].evidence_review_decision")
    handoff = _as_mapping(output.get("release_handoff"), f"evidence_review_outputs[{index}].release_handoff")
    return package, decision, handoff


def _row_from_outputs(outputs: Mapping[str, Any]) -> dict[str, Any]:
    package = _as_mapping(outputs.get("approved_release_package"), "approved_release_package")
    manifest = _as_mapping(outputs.get("approved_release_manifest"), "approved_release_manifest")
    handoff = _as_mapping(outputs.get("release_index_handoff"), "release_index_handoff")
    approved_release_id = _safe_id(package.get("approved_release_id"), label="approved_release_id")
    return {
        "adapter_id": _safe_text(package.get("adapter_id"), ""),
        "source_url": _safe_text(package.get("source_url"), ""),
        "queue_item_id": _safe_text(package.get("queue_item_id"), ""),
        "total_export_package_id": _safe_text(package.get("total_export_package_id"), ""),
        "capture_bundle_id": _safe_text(package.get("capture_bundle_id"), ""),
        "evidence_review_package_id": _safe_text(package.get("evidence_review_package_id"), ""),
        "approved_release_id": approved_release_id,
        "release_status": package.get("release_status", ""),
        "manifest_status": manifest.get("manifest_status", ""),
        "artifact_count": package.get("artifact_count", 0),
        "artifact_roles": list(package.get("artifact_roles", [])) if isinstance(package.get("artifact_roles"), list) else [],
        "handoff_status": handoff.get("handoff_status", ""),
        "required_next_stage": handoff.get("required_next_stage", ""),
        "release_fingerprint": package.get("release_fingerprint", ""),
    }


def build_source_adapter_approved_release_bridge(
    evidence_review_bridge_package: Mapping[str, Any],
    *,
    releaser_id: str = "manual_releaser",
    release_profile: str = "source_adapter_shared_approved_release_v1",
    release_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build shared Approved Release outputs from Adapter Evidence Review Bridge output."""

    package = _as_mapping(evidence_review_bridge_package, "evidence_review_bridge_package")
    if package.get("evidence_review_bridge_status") != "SHARED_EVIDENCE_REVIEWS_BUILT":
        raise ValueError("evidence review bridge package must be SHARED_EVIDENCE_REVIEWS_BUILT")
    handoff = package.get("source_adapter_approved_release_batch_handoff")
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != "READY_FOR_SHARED_APPROVED_RELEASE":
        raise ValueError("evidence review bridge handoff must be READY_FOR_SHARED_APPROVED_RELEASE")
    if handoff.get("ready_for_approved_release") is not True:
        raise ValueError("evidence review bridge handoff must be ready_for_approved_release")

    notes = _normalise_notes(release_notes)
    review_outputs = _review_outputs(package)
    if not review_outputs:
        raise ValueError("at least one Evidence Review output is required")

    approved_outputs: list[dict[str, Any]] = []
    approved_rows: list[dict[str, Any]] = []
    issue_rows: list[str] = []
    seen_release_ids: set[str] = set()

    for index, output in enumerate(review_outputs):
        evidence_review_package, decision, release_handoff = _review_output_parts(output, index)
        review_id = _safe_id(evidence_review_package.get("evidence_review_package_id"), label="evidence_review_package_id", fallback=f"evidence_review_{index}")
        try:
            outputs = build_source_approved_release(
                evidence_review_package=evidence_review_package,
                evidence_review_decision=decision,
                release_handoff=release_handoff,
                releaser_id=releaser_id,
                release_profile=release_profile,
                release_notes=notes,
            ).as_dict()
            row = _row_from_outputs(outputs)
        except Exception as exc:  # deterministic batch issue capture for operator review
            issue_rows.append(f"{review_id}: {exc}")
            continue
        if row["approved_release_id"] in seen_release_ids:
            issue_rows.append(f"duplicate approved release id: {row['approved_release_id']}")
            continue
        seen_release_ids.add(row["approved_release_id"])
        approved_outputs.append(dict(outputs))
        approved_rows.append(row)

    built = bool(approved_outputs) and not issue_rows
    approved_release_batch = {
        "schema_version": APPROVED_RELEASE_BATCH_SCHEMA_VERSION,
        "approved_release_count": len(approved_outputs),
        "approved_release_rows": approved_rows,
        "release_profile": release_profile,
    }
    release_index_handoff = {
        "schema_version": RELEASE_INDEX_HANDOFF_SCHEMA_VERSION,
        "handoff_status": RELEASE_INDEX_HANDOFF_STATUS if built else "APPROVED_RELEASE_BRIDGE_BLOCKED",
        "ready_for_release_index": built,
        "required_next_stage": "source_release_index",
        "approved_release_ids": [row["approved_release_id"] for row in approved_rows],
        "release_index_inputs": [
            {
                "role": "source_approved_release_package",
                "id": row["approved_release_id"],
                "filename_hint": f"{row['approved_release_id']}.source_approved_release_package.json",
            }
            for row in approved_rows
        ],
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": APPROVED_RELEASE_BRIDGE_STATUS if built else "APPROVED_RELEASE_BRIDGE_BLOCKED",
        "approved_release_count": len(approved_outputs),
        "issue_count": len(issue_rows),
        "release_profile": release_profile,
        "release_notes": notes,
        "implemented_stage": "source_approved_release",
        "next_actions": [
            "Pass approved-release outputs and release-index handoffs to the source_release_index stage.",
            "Keep Evidence Review decisions immutable and only release APPROVED review outputs.",
            "Use this shared approved-release bridge for future adapters unless a source has a genuinely unique release-shape requirement.",
        ],
    }
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "approved_release_bridge_status": APPROVED_RELEASE_BRIDGE_STATUS if built else "APPROVED_RELEASE_BRIDGE_BLOCKED",
        "source_adapter_evidence_review_bridge_id": _safe_text(package.get("source_adapter_evidence_review_bridge_id"), ""),
        "approved_release_count": len(approved_outputs),
        "issue_count": len(issue_rows),
        "issues": issue_rows,
        "approved_release_outputs": approved_outputs,
        "source_adapter_approved_release_batch": approved_release_batch,
        "source_adapter_release_index_batch_handoff": release_index_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "shared_stage_executed": "source_approved_release",
            "input_source": "source_adapter_evidence_review_bridge",
            "per_adapter_path": "approved_evidence_review_output_plus_shared_approved_release_builder",
            "multi_adapter_batch_supported": True,
        },
    }
    bridge_id = f"source_adapter_approved_release_bridge.{_stable_hash(unsigned)}"
    result = dict(unsigned)
    result["source_adapter_approved_release_bridge_id"] = bridge_id
    result["source_adapter_approved_release_batch"] = dict(approved_release_batch, source_adapter_approved_release_bridge_id=bridge_id)
    result["source_adapter_release_index_batch_handoff"] = dict(release_index_handoff, source_adapter_approved_release_bridge_id=bridge_id)
    result["operator_summary"] = dict(operator_summary, source_adapter_approved_release_bridge_id=bridge_id)
    return result


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_approved_release_bridge_package": dict(pkg),
        "source_adapter_approved_release_output_batch": deepcopy(pkg.get("approved_release_outputs", [])),
        "source_adapter_approved_release_batch": deepcopy(pkg.get("source_adapter_approved_release_batch", {})),
        "source_adapter_release_index_batch_handoff": deepcopy(pkg.get("source_adapter_release_index_batch_handoff", {})),
        "source_adapter_approved_release_bridge_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    from source_adapter_evidence_review_bridge import build_source_adapter_evidence_review_bridge
    from source_adapter_evidence_review_bridge_test import fixture_evidence_queue_bridge

    review_bridge = build_source_adapter_evidence_review_bridge(fixture_evidence_queue_bridge(), reviewer_decision={"decision": "APPROVED"})
    result = build_source_adapter_approved_release_bridge(review_bridge)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
