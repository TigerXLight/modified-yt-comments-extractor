from __future__ import annotations

import re
from typing import Any, Mapping

VERIFY_SCHEMA_VERSION = "source_adapter_capture_session_verifier_v1"
_EXPECTED_SCHEMA_VERSION = "source_adapter_capture_session_v1"
_EXPECTED_STATUS = "CAPTURE_SESSION_RECEIPTS_ACCEPTED"
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_SAFE_BASENAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def _safe_basename(value: Any) -> bool:
    text = str(value or "")
    return bool(text and _SAFE_BASENAME_RE.match(text) and ".." not in text and "/" not in text and "\\" not in text and not text.startswith((".", "-")))


def verify_source_adapter_capture_session(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if package.get("schema_version") != _EXPECTED_SCHEMA_VERSION:
        _issue(issues, "unexpected schema_version")
    if package.get("capture_session_status") != _EXPECTED_STATUS:
        _issue(issues, "capture_session_status must be CAPTURE_SESSION_RECEIPTS_ACCEPTED")
    session_id = str(package.get("source_adapter_capture_session_id") or "")
    if not session_id.startswith("source_adapter_capture_session."):
        _issue(issues, "source_adapter_capture_session_id is missing or invalid")
    adapters = package.get("adapters")
    if not isinstance(adapters, list) or not adapters:
        _issue(issues, "adapters must be a non-empty list")
    receipts = package.get("artifact_receipts")
    if not isinstance(receipts, list) or not receipts:
        _issue(issues, "artifact_receipts must be a non-empty list")
    else:
        seen: set[tuple[str, str]] = set()
        for receipt in receipts:
            if not isinstance(receipt, Mapping):
                _issue(issues, "artifact receipt must be a mapping")
                continue
            pair = (str(receipt.get("adapter_id") or ""), str(receipt.get("artifact_role") or ""))
            if not pair[0] or not pair[1]:
                _issue(issues, "artifact receipt must include adapter_id and artifact_role")
            if pair in seen:
                _issue(issues, f"duplicate receipt pair: {pair[0]}/{pair[1]}")
            seen.add(pair)
            if not _safe_basename(receipt.get("artifact_basename")):
                _issue(issues, "artifact_basename must be a safe basename")
            if not isinstance(receipt.get("byte_count"), int) or receipt.get("byte_count") < 0:
                _issue(issues, "byte_count must be a non-negative integer")
            digest = str(receipt.get("sha256") or "")
            if not _SHA256_RE.match(digest):
                _issue(issues, "sha256 must be a 64-character lowercase hex digest")
    if package.get("safety_contract", {}).get("artifact_bytes_read_by_this_stage") is not False:
        _issue(issues, "safety contract must keep artifact byte reads out of this stage")
    if package.get("safety_contract", {}).get("manual_or_live_actions_started_by_this_stage") is not False:
        _issue(issues, "safety contract must not start manual/live actions")
    handoff = package.get("artifact_collection_handoff")
    if not isinstance(handoff, Mapping) or handoff.get("ready_for_source_artifact_collection") is not True:
        _issue(issues, "artifact collection handoff must be ready")
    return {
        "schema_version": VERIFY_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_capture_session_id": session_id,
        "source_adapter_capture_action_kit_id": package.get("source_adapter_capture_action_kit_id", ""),
        "receipt_count": package.get("receipt_count", 0),
        "adapter_count": package.get("adapter_count", 0),
        "capture_session_status": package.get("capture_session_status", ""),
    }
