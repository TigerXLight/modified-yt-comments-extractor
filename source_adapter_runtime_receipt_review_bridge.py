from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "source_adapter_runtime_receipt_review_bridge_v1"
REVIEW_BATCH_SCHEMA_VERSION = "source_adapter_runtime_receipt_review_batch_v1"
ACCEPTANCE_INDEX_SCHEMA_VERSION = "source_adapter_runtime_acceptance_index_v1"
ACCEPTANCE_HANDOFF_SCHEMA_VERSION = "source_adapter_runtime_acceptance_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_runtime_receipt_review_bridge_operator_summary_v1"
RUNTIME_RECEIPT_REVIEW_STATUS = "SOURCE_ADAPTER_RUNTIME_RECEIPTS_REVIEWED"
RUNTIME_ACCEPTANCE_READY_STATUS = "SOURCE_ADAPTER_RUNTIME_READY_FOR_UI_OR_PROVIDER_INTEGRATION"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_ACCEPTED_DECISIONS = {"ACCEPTED", "ACCEPTED_WITH_NOTES"}
_DEFAULT_REQUIRED_CAPABILITIES = (
    "operator_url_fetch",
    "browser_launch",
    "folder_scan",
    "credential_lookup",
    "archive_submit",
    "release_upload",
    "app_registry_mutation",
    "file_library_publication",
)


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
        raise ValueError(f"{label} must contain only letters, numbers, dot, colon, underscore, or dash")
    return text


def _normalise_notes(notes: Iterable[str] | None) -> list[str]:
    return [str(note).strip() for note in (notes or []) if str(note).strip()]


def _normalise_required_capabilities(required_capabilities: Iterable[str] | None) -> list[str]:
    values = list(required_capabilities or _DEFAULT_REQUIRED_CAPABILITIES)
    normalised = [_safe_id(item, label="required capability") for item in values]
    seen: set[str] = set()
    result: list[str] = []
    for item in normalised:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _runtime_actions(runtime_wiring_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    batch = _as_mapping(runtime_wiring_bridge_package.get("source_adapter_runtime_action_batch"), "source_adapter_runtime_action_batch")
    return _as_mapping_list(batch.get("runtime_actions"), "runtime_actions")


def _runtime_receipts(runtime_wiring_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    batch = _as_mapping(
        runtime_wiring_bridge_package.get("source_adapter_runtime_action_receipt_batch"),
        "source_adapter_runtime_action_receipt_batch",
    )
    receipts = batch.get("runtime_action_receipts") or []
    return _as_mapping_list(receipts, "runtime_action_receipts")


def _receipt_lookup(receipts: list[Mapping[str, Any]]) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    lookup: dict[str, Mapping[str, Any]] = {}
    issues: list[str] = []
    for index, receipt in enumerate(receipts):
        action_id = _safe_text(receipt.get("runtime_action_id"), "")
        if not action_id:
            issues.append(f"runtime_action_receipts[{index}] missing runtime_action_id")
            continue
        if action_id in lookup:
            issues.append(f"duplicate receipt for runtime action: {action_id}")
            continue
        lookup[action_id] = receipt
    return lookup, issues


def _classify_effect(receipt: Mapping[str, Any]) -> str:
    if receipt.get("execution_mode") == "dry_run":
        return "dry_run_fixture_receipt"
    if bool(receipt.get("external_effect_recorded")):
        return "operator_recorded_runtime_effect"
    return "runtime_request_receipt"


def _review_row(
    action: Mapping[str, Any],
    receipt: Mapping[str, Any] | None,
    index: int,
    *,
    reviewer_id: str,
    acceptance_decision: str,
) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    runtime_action_id = _safe_id(action.get("runtime_action_id"), label="runtime_action_id")
    capability_id = _safe_id(action.get("capability_id"), label="capability_id")
    if receipt is None:
        issues.append(f"{runtime_action_id}: missing runtime action receipt")
        execution_status = "MISSING_RUNTIME_RECEIPT"
        receipt_id = ""
        execution_mode = _safe_text(action.get("execution_mode"), "")
        effect_classification = "receipt_required"
        external_effect_recorded = False
        row_decision = "RECEIPT_REQUIRED"
    else:
        receipt_id = _safe_text(receipt.get("runtime_action_receipt_id"), "")
        if not receipt_id:
            issues.append(f"{runtime_action_id}: runtime receipt id is required")
        if receipt.get("capability_id") != capability_id:
            issues.append(f"{runtime_action_id}: receipt capability mismatch")
        execution_status = _safe_text(receipt.get("execution_status"), "")
        if not execution_status:
            issues.append(f"{runtime_action_id}: execution_status is required")
        execution_mode = _safe_text(receipt.get("execution_mode"), "")
        effect_classification = _classify_effect(receipt)
        external_effect_recorded = bool(receipt.get("external_effect_recorded"))
        row_decision = acceptance_decision if not issues else "REVIEW_ISSUES"
    unsigned = {
        "schema_version": "source_adapter_runtime_receipt_review_row_v1",
        "runtime_action_id": runtime_action_id,
        "runtime_action_receipt_id": receipt_id,
        "capability_id": capability_id,
        "adapter_id": _safe_text(action.get("adapter_id"), ""),
        "source_url": _safe_text(action.get("source_url"), ""),
        "source_pipeline_closeout_id": _safe_text(action.get("source_pipeline_closeout_id"), ""),
        "approval_id": _safe_text(action.get("approval_id"), ""),
        "approval_status": _safe_text(action.get("approval_status"), ""),
        "execution_mode": execution_mode,
        "execution_status": execution_status,
        "external_effect_recorded": external_effect_recorded,
        "runtime_effect_classification": effect_classification,
        "review_decision": row_decision,
        "reviewer_id": reviewer_id,
        "review_index": index,
    }
    return dict(unsigned, runtime_receipt_review_row_id=f"source_adapter.runtime_receipt_review_row.{_stable_hash(unsigned)}"), issues


def build_source_adapter_runtime_receipt_review_bridge(
    runtime_wiring_bridge_package: Mapping[str, Any],
    *,
    required_capabilities: Iterable[str] | None = None,
    acceptance_decision: str = "ACCEPTED",
    reviewer_id: str = "operator",
    review_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Review runtime action receipts emitted by the shared runtime wiring bridge."""

    package = _as_mapping(runtime_wiring_bridge_package, "runtime_wiring_bridge_package")
    if package.get("runtime_wiring_status") != "SOURCE_ADAPTER_RUNTIME_ACTIONS_WIRED":
        raise ValueError("runtime wiring bridge package must be SOURCE_ADAPTER_RUNTIME_ACTIONS_WIRED")
    handoff = _as_mapping(package.get("source_adapter_runtime_execution_handoff"), "source_adapter_runtime_execution_handoff")
    if handoff.get("required_next_stage") != "source_adapter_runtime_receipt_review":
        raise ValueError("runtime execution handoff must request source_adapter_runtime_receipt_review")
    if acceptance_decision not in _ACCEPTED_DECISIONS:
        raise ValueError("acceptance_decision must be ACCEPTED or ACCEPTED_WITH_NOTES")
    reviewer_id = _safe_id(reviewer_id, label="reviewer_id")
    required = _normalise_required_capabilities(required_capabilities)
    notes = _normalise_notes(review_notes)

    actions = _runtime_actions(package)
    receipts = _runtime_receipts(package)
    receipt_by_action, issues = _receipt_lookup(receipts)
    if not actions:
        issues.append("runtime action batch must contain at least one action")

    review_rows: list[dict[str, Any]] = []
    for index, action in enumerate(actions):
        try:
            row, row_issues = _review_row(
                action,
                receipt_by_action.get(_safe_text(action.get("runtime_action_id"), "")),
                index,
                reviewer_id=reviewer_id,
                acceptance_decision=acceptance_decision,
            )
            review_rows.append(row)
            issues.extend(row_issues)
        except Exception as exc:
            issues.append(f"runtime_actions[{index}]: {exc}")

    action_ids = {_safe_text(action.get("runtime_action_id"), "") for action in actions}
    for receipt_action_id in sorted(receipt_by_action):
        if receipt_action_id not in action_ids:
            issues.append(f"receipt references unknown runtime action: {receipt_action_id}")

    accepted_rows = [row for row in review_rows if row.get("review_decision") in _ACCEPTED_DECISIONS]
    accepted_capabilities = sorted({_safe_text(row.get("capability_id"), "") for row in accepted_rows})
    missing_required = sorted(set(required) - set(accepted_capabilities))
    if missing_required:
        issues.append(f"missing required accepted runtime capabilities: {missing_required}")

    review_status = RUNTIME_RECEIPT_REVIEW_STATUS if not issues else "SOURCE_ADAPTER_RUNTIME_RECEIPT_REVIEW_HAS_ISSUES"
    acceptance_status = RUNTIME_ACCEPTANCE_READY_STATUS if not issues else "SOURCE_ADAPTER_RUNTIME_ACCEPTANCE_REVIEW_REQUIRED"
    review_batch = {
        "schema_version": REVIEW_BATCH_SCHEMA_VERSION,
        "runtime_action_count": len(actions),
        "runtime_receipt_count": len(receipts),
        "runtime_receipt_review_count": len(review_rows),
        "accepted_review_count": len(accepted_rows),
        "review_rows": review_rows,
    }
    acceptance_index = {
        "schema_version": ACCEPTANCE_INDEX_SCHEMA_VERSION,
        "acceptance_status": acceptance_status,
        "accepted_capability_count": len(accepted_capabilities),
        "accepted_capability_ids": accepted_capabilities,
        "required_capability_ids": required,
        "runtime_action_ids": [row["runtime_action_id"] for row in accepted_rows],
        "runtime_action_receipt_ids": [row["runtime_action_receipt_id"] for row in accepted_rows if row.get("runtime_action_receipt_id")],
    }
    acceptance_handoff = {
        "schema_version": ACCEPTANCE_HANDOFF_SCHEMA_VERSION,
        "handoff_status": acceptance_status,
        "ready_for_runtime_ui_provider_integration": not issues,
        "required_next_stage": "source_adapter_runtime_ui_provider_integration",
        "accepted_capability_ids": accepted_capabilities,
        "source_adapter_runtime_wiring_bridge_id": _safe_text(package.get("source_adapter_runtime_wiring_bridge_id"), ""),
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": review_status,
        "reviewer_id": reviewer_id,
        "acceptance_decision": acceptance_decision,
        "runtime_action_count": len(actions),
        "runtime_receipt_count": len(receipts),
        "accepted_review_count": len(accepted_rows),
        "issue_count": len(issues),
        "review_notes": notes,
        "next_actions": [
            "Bind accepted runtime capability IDs to shared UI and CLI surfaces.",
            "Carry runtime receipt review rows into provider integration and fixture acceptance evidence.",
            "Use the same action and receipt identifiers for browser, archive, credential, folder, release, registry, and library operations.",
        ],
    }
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "runtime_receipt_review_status": review_status,
        "source_adapter_runtime_wiring_bridge_id": _safe_text(package.get("source_adapter_runtime_wiring_bridge_id"), ""),
        "runtime_action_count": len(actions),
        "runtime_receipt_count": len(receipts),
        "runtime_receipt_review_count": len(review_rows),
        "accepted_review_count": len(accepted_rows),
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_runtime_receipt_review_batch": review_batch,
        "source_adapter_runtime_acceptance_index": acceptance_index,
        "source_adapter_runtime_acceptance_handoff": acceptance_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "shared_stage_executed": "source_adapter_runtime_receipt_review",
            "input_stage": "source_adapter_runtime_wiring_bridge",
            "runtime_action_receipts_reviewed": True,
            "runtime_acceptance_handoff_built": True,
            "batch_supported": True,
        },
    }
    bridge_id = f"source_adapter_runtime_receipt_review_bridge.{_stable_hash(unsigned)}"
    result = dict(unsigned, source_adapter_runtime_receipt_review_bridge_id=bridge_id)
    result["source_adapter_runtime_receipt_review_batch"] = dict(review_batch, source_adapter_runtime_receipt_review_bridge_id=bridge_id)
    result["source_adapter_runtime_acceptance_index"] = dict(acceptance_index, source_adapter_runtime_receipt_review_bridge_id=bridge_id)
    result["source_adapter_runtime_acceptance_handoff"] = dict(acceptance_handoff, source_adapter_runtime_receipt_review_bridge_id=bridge_id)
    result["operator_summary"] = dict(operator_summary, source_adapter_runtime_receipt_review_bridge_id=bridge_id)
    return result


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_runtime_receipt_review_bridge_package": dict(pkg),
        "source_adapter_runtime_receipt_review_batch": deepcopy(pkg.get("source_adapter_runtime_receipt_review_batch", {})),
        "source_adapter_runtime_acceptance_index": deepcopy(pkg.get("source_adapter_runtime_acceptance_index", {})),
        "source_adapter_runtime_acceptance_handoff": deepcopy(pkg.get("source_adapter_runtime_acceptance_handoff", {})),
        "source_adapter_runtime_receipt_review_bridge_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    from source_adapter_runtime_receipt_review_bridge_test import fixture_runtime_wiring_bridge

    package = build_source_adapter_runtime_receipt_review_bridge(
        fixture_runtime_wiring_bridge(),
        review_notes=["manual self-test fixture"],
    )
    print(json.dumps(package, indent=2, sort_keys=True, ensure_ascii=False))
