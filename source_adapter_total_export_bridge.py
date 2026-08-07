from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping

from source_total_export_package import build_source_total_export_package

SCHEMA_VERSION = "source_adapter_total_export_bridge_v1"
PACKAGE_INDEX_SCHEMA_VERSION = "source_adapter_total_export_package_index_v1"
EVIDENCE_QUEUE_HANDOFF_SCHEMA_VERSION = "source_adapter_evidence_queue_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_total_export_bridge_operator_summary_v1"
TOTAL_EXPORT_BRIDGE_STATUS = "SHARED_TOTAL_EXPORT_PACKAGES_BUILT"
EVIDENCE_QUEUE_HANDOFF_STATUS = "READY_FOR_SHARED_EVIDENCE_QUEUE"

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


def _capture_bundle_outputs(capture_bundle_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _as_mapping_list(capture_bundle_bridge_package.get("capture_bundle_outputs"), "capture_bundle_outputs")


def _output_bundle(output: Mapping[str, Any], index: int) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    bundle = _as_mapping(output.get("capture_bundle"), f"capture_bundle_outputs[{index}].capture_bundle")
    manifest = _as_mapping(output.get("capture_manifest"), f"capture_bundle_outputs[{index}].capture_manifest")
    handoff = _as_mapping(output.get("total_export_handoff"), f"capture_bundle_outputs[{index}].total_export_handoff")
    return bundle, manifest, handoff


def _row_from_outputs(outputs: Mapping[str, Any]) -> dict[str, Any]:
    package = _as_mapping(outputs.get("total_export_package"), "total_export_package")
    manifest = _as_mapping(outputs.get("total_export_manifest"), "total_export_manifest")
    handoff = _as_mapping(outputs.get("evidence_queue_handoff"), "evidence_queue_handoff")
    package_id = _safe_id(package.get("total_export_package_id"), label="total_export_package_id")
    return {
        "adapter_id": _safe_text(package.get("adapter_id"), ""),
        "source_url": _safe_text(package.get("source_url"), ""),
        "capture_bundle_id": _safe_text(package.get("capture_bundle_id"), ""),
        "total_export_package_id": package_id,
        "artifact_count": manifest.get("artifact_count", 0),
        "comment_count": manifest.get("comment_count", 0),
        "export_status": package.get("export_status", ""),
        "handoff_status": handoff.get("handoff_status", ""),
    }


def build_source_adapter_total_export_bridge(
    capture_bundle_bridge_package: Mapping[str, Any],
    *,
    export_profile: str = "source_adapter_shared_v1",
    package_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build shared Total Export packages from Adapter Capture Bundle Bridge output."""

    package = _as_mapping(capture_bundle_bridge_package, "capture_bundle_bridge_package")
    if package.get("capture_bundle_bridge_status") != "SHARED_CAPTURE_BUNDLES_BUILT":
        raise ValueError("capture bundle bridge package must be SHARED_CAPTURE_BUNDLES_BUILT")
    handoff = package.get("source_adapter_total_export_handoff")
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != "READY_FOR_SHARED_TOTAL_EXPORT_PACKAGE":
        raise ValueError("capture bundle bridge handoff must be READY_FOR_SHARED_TOTAL_EXPORT_PACKAGE")

    notes = _normalise_notes(package_notes)
    bundle_outputs = _capture_bundle_outputs(package)
    if not bundle_outputs:
        raise ValueError("at least one capture bundle output is required")

    total_export_outputs: list[dict[str, Any]] = []
    package_rows: list[dict[str, Any]] = []
    issue_rows: list[str] = []
    seen_package_ids: set[str] = set()

    for index, output in enumerate(bundle_outputs):
        bundle, manifest, total_handoff = _output_bundle(output, index)
        try:
            outputs = build_source_total_export_package(
                capture_bundle=bundle,
                capture_manifest=manifest,
                total_export_handoff=total_handoff,
                export_profile=export_profile,
                package_notes=notes,
            ).as_dict()
            row = _row_from_outputs(outputs)
        except Exception as exc:  # deterministic batch issue capture for operator review
            bundle_id = _safe_text(bundle.get("capture_bundle_id"), f"capture_bundle_{index}") if isinstance(bundle, Mapping) else f"capture_bundle_{index}"
            issue_rows.append(f"{bundle_id}: {exc}")
            continue
        if row["total_export_package_id"] in seen_package_ids:
            issue_rows.append(f"duplicate total export package id: {row['total_export_package_id']}")
            continue
        seen_package_ids.add(row["total_export_package_id"])
        total_export_outputs.append(dict(outputs))
        package_rows.append(row)

    ready = bool(total_export_outputs) and not issue_rows
    package_index = {
        "schema_version": PACKAGE_INDEX_SCHEMA_VERSION,
        "total_export_package_count": len(total_export_outputs),
        "package_rows": package_rows,
    }
    evidence_queue_handoff = {
        "schema_version": EVIDENCE_QUEUE_HANDOFF_SCHEMA_VERSION,
        "handoff_status": EVIDENCE_QUEUE_HANDOFF_STATUS if ready else "TOTAL_EXPORT_BRIDGE_BLOCKED",
        "ready_for_evidence_queue": ready,
        "required_next_stage": "source_evidence_queue",
        "total_export_package_ids": [row["total_export_package_id"] for row in package_rows],
        "evidence_queue_inputs": [
            {
                "role": "source_total_export_package",
                "id": row["total_export_package_id"],
                "filename_hint": f"{row['total_export_package_id']}.source_total_export_package.json",
            }
            for row in package_rows
        ],
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": TOTAL_EXPORT_BRIDGE_STATUS if ready else "TOTAL_EXPORT_BRIDGE_BLOCKED",
        "total_export_package_count": len(total_export_outputs),
        "issue_count": len(issue_rows),
        "export_profile": export_profile,
        "package_notes": notes,
        "implemented_stage": "source_total_export_package",
        "next_actions": [
            "Pass the Total Export package batch and Evidence Queue handoff to the shared evidence queue stage.",
            "Use the package index to review multi-source package readiness before evidence queue intake.",
            "Keep adapter-specific code limited to genuinely different extraction or export shape requirements.",
        ],
    }
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "total_export_bridge_status": TOTAL_EXPORT_BRIDGE_STATUS if ready else "TOTAL_EXPORT_BRIDGE_BLOCKED",
        "source_adapter_capture_bundle_bridge_id": _safe_text(package.get("source_adapter_capture_bundle_bridge_id"), ""),
        "total_export_package_count": len(total_export_outputs),
        "issue_count": len(issue_rows),
        "issues": issue_rows,
        "total_export_outputs": total_export_outputs,
        "source_adapter_total_export_package_index": package_index,
        "source_adapter_evidence_queue_handoff": evidence_queue_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "shared_stage_executed": "source_total_export_package",
            "input_source": "source_adapter_capture_bundle_bridge",
            "per_adapter_path": "capture_bundle_plus_shared_total_export_builder",
            "multi_adapter_batch_supported": True,
        },
    }
    bridge_id = f"source_adapter_total_export_bridge.{_stable_hash(unsigned)}"
    result = dict(unsigned)
    result["source_adapter_total_export_bridge_id"] = bridge_id
    result["source_adapter_total_export_package_index"] = dict(package_index, source_adapter_total_export_bridge_id=bridge_id)
    result["source_adapter_evidence_queue_handoff"] = dict(evidence_queue_handoff, source_adapter_total_export_bridge_id=bridge_id)
    result["operator_summary"] = dict(operator_summary, source_adapter_total_export_bridge_id=bridge_id)
    return result


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_total_export_bridge_package": dict(pkg),
        "source_adapter_total_export_package_batch": deepcopy(pkg.get("total_export_outputs", [])),
        "source_adapter_total_export_package_index": deepcopy(pkg.get("source_adapter_total_export_package_index", {})),
        "source_adapter_evidence_queue_handoff": deepcopy(pkg.get("source_adapter_evidence_queue_handoff", {})),
        "source_adapter_total_export_bridge_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    from source_adapter_capture_bundle_bridge_test import fixture_extraction_bridge
    from source_adapter_capture_bundle_bridge import build_source_adapter_capture_bundle_bridge

    bridge_input = build_source_adapter_capture_bundle_bridge(fixture_extraction_bridge())
    result = build_source_adapter_total_export_bridge(bridge_input)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
