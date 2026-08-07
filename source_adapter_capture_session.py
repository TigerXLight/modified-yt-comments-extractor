from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "source_adapter_capture_session_v1"
SESSION_RECORD_SCHEMA_VERSION = "source_adapter_capture_session_record_v1"
RECEIPT_INDEX_SCHEMA_VERSION = "source_adapter_capture_artifact_receipt_index_v1"
ARTIFACT_COLLECTION_HANDOFF_SCHEMA_VERSION = "source_adapter_artifact_collection_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_capture_session_operator_summary_v1"
CAPTURE_SESSION_STATUS = "CAPTURE_SESSION_RECEIPTS_ACCEPTED"
ARTIFACT_COLLECTION_HANDOFF_STATUS = "READY_FOR_EXPLICIT_ARTIFACT_COLLECTION"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_SAFE_BASENAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")

FORBIDDEN_RUNTIME_EFFECTS = [
    "fetch_url",
    "launch_browser",
    "scan_folder",
    "read_credentials",
    "submit_archive",
    "upload_release",
    "mutate_app_files",
    "mutate_registry_files",
    "start_live_action",
]


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _stable_hash(value: Any, *, length: int = 12) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()[:length]


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return value


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _safe_id(value: Any, *, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} is required")
    if not _SAFE_ID_RE.match(text):
        raise ValueError(f"{label} must be a safe identifier: {text!r}")
    if ".." in text or text.startswith((".", "-")):
        raise ValueError(f"{label} must not contain traversal-like segments: {text!r}")
    return text


def _safe_basename(value: Any, *, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} is required")
    if not _SAFE_BASENAME_RE.match(text):
        raise ValueError(f"{label} must be a safe basename: {text!r}")
    if ".." in text or text.startswith((".", "-")) or "/" in text or "\\" in text:
        raise ValueError(f"{label} must be a safe basename with no path separators: {text!r}")
    return text


def _safe_text(value: Any, default: str = "") -> str:
    text = str(value or default).strip()
    return text if text else default


def _positive_or_zero_int(value: Any, *, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an integer") from exc
    if number < 0:
        raise ValueError(f"{label} must be non-negative")
    return number


def _sha256(value: Any, *, label: str) -> str:
    text = str(value or "").strip().lower()
    if not _SHA256_RE.match(text):
        raise ValueError(f"{label} must be a 64-character SHA-256 hex digest")
    return text


def _unique_strings(values: Sequence[Any]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _extract_templates(action_kit_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    template_doc = action_kit_package.get("artifact_intake_templates") or action_kit_package.get(
        "source_adapter_capture_artifact_intake_templates"
    )
    if isinstance(template_doc, Mapping):
        templates = template_doc.get("templates")
        if isinstance(templates, list) and templates:
            return [_as_mapping(template, "artifact intake template") for template in templates]
    direct_templates = action_kit_package.get("templates")
    if isinstance(direct_templates, list) and direct_templates:
        return [_as_mapping(template, "artifact intake template") for template in direct_templates]
    raise ValueError("action kit package must contain artifact intake templates")


def _extract_adapters(action_kit_package: Mapping[str, Any], templates: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    raw_adapters = action_kit_package.get("adapters")
    adapters: list[dict[str, Any]] = []
    if isinstance(raw_adapters, list) and raw_adapters:
        for raw_adapter in raw_adapters:
            adapter = _as_mapping(raw_adapter, "adapter")
            adapters.append(
                {
                    "adapter_id": _safe_id(adapter.get("adapter_id") or adapter.get("id"), label="adapter_id"),
                    "display_name": _safe_text(adapter.get("display_name"), _safe_text(adapter.get("adapter_id"), "Adapter")),
                    "source_kind": _safe_text(adapter.get("source_kind"), "web"),
                    "artifact_roles": [_safe_id(role, label="artifact role") for role in _unique_strings(_as_list(adapter.get("artifact_roles")))],
                }
            )
    if not adapters:
        grouped: dict[str, list[str]] = {}
        for template in templates:
            adapter_id = _safe_id(template.get("adapter_id"), label="template adapter_id")
            role = _safe_id(template.get("artifact_role"), label="template artifact_role")
            grouped.setdefault(adapter_id, []).append(role)
        adapters = [
            {
                "adapter_id": adapter_id,
                "display_name": adapter_id.replace("_", " ").title(),
                "source_kind": "web",
                "artifact_roles": _unique_strings(roles),
            }
            for adapter_id, roles in sorted(grouped.items())
        ]
    if not adapters:
        raise ValueError("action kit package must contain at least one adapter")
    return adapters


def _required_role_pairs(templates: list[Mapping[str, Any]]) -> set[tuple[str, str]]:
    required: set[tuple[str, str]] = set()
    for template in templates:
        adapter_id = _safe_id(template.get("adapter_id"), label="template adapter_id")
        role = _safe_id(template.get("artifact_role"), label="template artifact_role")
        required.add((adapter_id, role))
    return required


def _receipt_list(artifact_receipts: Any) -> list[Any]:
    if isinstance(artifact_receipts, Mapping):
        for key in ("artifact_receipts", "receipts", "artifacts", "stored_files"):
            value = artifact_receipts.get(key)
            if isinstance(value, list):
                return value
    if isinstance(artifact_receipts, list):
        return artifact_receipts
    raise TypeError("artifact_receipts must be a list or a mapping containing artifact_receipts")


def _normalise_receipt(raw_receipt: Mapping[str, Any], required_pairs: set[tuple[str, str]]) -> dict[str, Any]:
    adapter_id = _safe_id(raw_receipt.get("adapter_id"), label="receipt adapter_id")
    role = _safe_id(raw_receipt.get("artifact_role") or raw_receipt.get("role"), label="receipt artifact_role")
    pair = (adapter_id, role)
    if pair not in required_pairs:
        raise ValueError(f"receipt does not match action kit templates: {adapter_id}/{role}")
    basename = _safe_basename(
        raw_receipt.get("artifact_basename") or raw_receipt.get("filename"),
        label="artifact_basename",
    )
    byte_count = _positive_or_zero_int(raw_receipt.get("byte_count"), label="byte_count")
    digest = _sha256(raw_receipt.get("sha256"), label="sha256")
    receipt_id = _safe_id(raw_receipt.get("receipt_id") or f"{adapter_id}.{role}.{basename}", label="receipt_id")
    source_url = _safe_text(raw_receipt.get("source_url"), "")
    return {
        "receipt_id": receipt_id,
        "adapter_id": adapter_id,
        "artifact_role": role,
        "artifact_basename": basename,
        "byte_count": byte_count,
        "sha256": digest,
        "source_url": source_url,
        "operator_supplied": True,
        "artifact_bytes_read_by_this_stage": False,
    }


def _normalise_receipts(artifact_receipts: Any, required_pairs: set[tuple[str, str]]) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    seen_basenames: set[str] = set()
    for raw in _receipt_list(artifact_receipts):
        receipt = _normalise_receipt(_as_mapping(raw, "artifact receipt"), required_pairs)
        pair = (receipt["adapter_id"], receipt["artifact_role"])
        if pair in seen_pairs:
            raise ValueError(f"duplicate receipt for adapter/role: {pair[0]}/{pair[1]}")
        if receipt["artifact_basename"] in seen_basenames:
            raise ValueError(f"duplicate artifact basename: {receipt['artifact_basename']}")
        seen_pairs.add(pair)
        seen_basenames.add(receipt["artifact_basename"])
        receipts.append(receipt)
    if not receipts:
        raise ValueError("at least one artifact receipt is required")
    missing = sorted(required_pairs - seen_pairs)
    if missing:
        missing_text = ", ".join(f"{adapter}/{role}" for adapter, role in missing)
        raise ValueError(f"missing required artifact receipts: {missing_text}")
    return receipts


def build_source_adapter_capture_session(
    action_kit_package: Mapping[str, Any],
    artifact_receipts: Any,
    *,
    operator_approval_id: str = "",
    session_notes: str = "",
) -> dict[str, Any]:
    """Build a deterministic capture session package from explicit operator receipt metadata."""

    source_package = _as_mapping(action_kit_package, "action_kit_package")
    templates = _extract_templates(source_package)
    adapters = _extract_adapters(source_package, templates)
    required_pairs = _required_role_pairs(templates)
    receipts = _normalise_receipts(artifact_receipts, required_pairs)
    source_adapter_capture_action_kit_id = _safe_text(source_package.get("source_adapter_capture_action_kit_id"), "")
    approval_id = _safe_id(operator_approval_id, label="operator_approval_id") if operator_approval_id else ""

    receipt_index = {
        "schema_version": RECEIPT_INDEX_SCHEMA_VERSION,
        "receipt_count": len(receipts),
        "adapter_count": len(adapters),
        "receipts": receipts,
    }
    session_record = {
        "schema_version": SESSION_RECORD_SCHEMA_VERSION,
        "capture_session_status": CAPTURE_SESSION_STATUS,
        "source_adapter_capture_action_kit_id": source_adapter_capture_action_kit_id,
        "operator_approval_id": approval_id,
        "adapter_count": len(adapters),
        "receipt_count": len(receipts),
        "artifact_bytes_read_by_this_stage": False,
        "manual_or_live_actions_started_by_this_stage": False,
        "session_notes": _safe_text(session_notes, ""),
    }
    artifact_collection_handoff = {
        "schema_version": ARTIFACT_COLLECTION_HANDOFF_SCHEMA_VERSION,
        "status": ARTIFACT_COLLECTION_HANDOFF_STATUS,
        "source_adapter_capture_action_kit_id": source_adapter_capture_action_kit_id,
        "receipt_count": len(receipts),
        "adapter_count": len(adapters),
        "ready_for_source_artifact_collection": True,
        "requires_explicit_artifact_files": True,
        "artifact_receipts_validated": True,
        "artifact_bytes_read_by_this_stage": False,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": CAPTURE_SESSION_STATUS,
        "adapter_count": len(adapters),
        "receipt_count": len(receipts),
        "live_network_default": False,
        "manual_or_live_actions_started_by_this_stage": False,
        "next_actions": [
            "Pass the receipt index and explicit local artifacts to the shared artifact collection stage.",
            "Keep artifact byte validation inside explicit artifact collection, not this planning/intake stage.",
            "Do not infer files from folders; use only operator-supplied basenames, byte counts, and hashes.",
        ],
    }

    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "capture_session_status": CAPTURE_SESSION_STATUS,
        "source_adapter_capture_action_kit_id": source_adapter_capture_action_kit_id,
        "adapters": deepcopy(adapters),
        "adapter_count": len(adapters),
        "artifact_receipts": receipts,
        "receipt_count": len(receipts),
        "capture_session_record": session_record,
        "artifact_receipt_index": receipt_index,
        "artifact_collection_handoff": artifact_collection_handoff,
        "operator_summary": operator_summary,
        "safety_contract": {
            "live_network_default": False,
            "manual_or_live_actions_started_by_this_stage": False,
            "artifact_bytes_read_by_this_stage": False,
            "forbidden_runtime_effects": list(FORBIDDEN_RUNTIME_EFFECTS),
        },
    }
    session_id = f"source_adapter_capture_session.{_stable_hash(unsigned)}"
    package = dict(unsigned)
    package["source_adapter_capture_session_id"] = session_id
    package["capture_session_record"] = dict(session_record, source_adapter_capture_session_id=session_id)
    package["artifact_receipt_index"] = dict(receipt_index, source_adapter_capture_session_id=session_id)
    package["artifact_collection_handoff"] = dict(artifact_collection_handoff, source_adapter_capture_session_id=session_id)
    package["operator_summary"] = dict(operator_summary, source_adapter_capture_session_id=session_id)
    return package


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_capture_session_package": dict(pkg),
        "source_adapter_capture_session_record": deepcopy(pkg.get("capture_session_record", {})),
        "source_adapter_capture_artifact_receipt_index": deepcopy(pkg.get("artifact_receipt_index", {})),
        "source_adapter_artifact_collection_handoff": deepcopy(pkg.get("artifact_collection_handoff", {})),
        "source_adapter_capture_session_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    sample_action_kit = {
        "source_adapter_capture_action_kit_id": "source_adapter_capture_action_kit.example",
        "adapters": [{"adapter_id": "article", "artifact_roles": ["article_html_or_text"]}],
        "artifact_intake_templates": {"templates": [{"adapter_id": "article", "artifact_role": "article_html_or_text"}]},
    }
    sample_receipts = [
        {
            "adapter_id": "article",
            "artifact_role": "article_html_or_text",
            "artifact_basename": "article.html",
            "byte_count": 42,
            "sha256": "a" * 64,
        }
    ]
    built = build_source_adapter_capture_session(sample_action_kit, sample_receipts, operator_approval_id="approval.example")
    assert built["capture_session_status"] == CAPTURE_SESSION_STATUS
    assert built["artifact_collection_handoff"]["ready_for_source_artifact_collection"] is True
    print("Source Adapter Capture Session self-test passed.")
