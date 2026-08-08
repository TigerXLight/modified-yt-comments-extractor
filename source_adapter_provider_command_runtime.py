from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from source_adapter_operator_approved_execution_runtime import (
    KEYS_ACCOUNTS_LABEL,
    PROVIDER_ACTIONS,
    SCHEMA_VERSION as OPERATOR_RUNTIME_SCHEMA_VERSION,
    STATUS as OPERATOR_RUNTIME_STATUS,
    example_operator_approved_execution_runtime_package,
)

SCHEMA_VERSION = "source_adapter_provider_command_runtime_v1"
REQUEST_MATRIX_SCHEMA_VERSION = "source_adapter_provider_command_request_matrix_v1"
REQUEST_SCHEMA_VERSION = "source_adapter_provider_command_request_row_v1"
RECEIPT_BATCH_SCHEMA_VERSION = "source_adapter_provider_command_execution_receipt_batch_v1"
RECEIPT_SCHEMA_VERSION = "source_adapter_provider_command_execution_receipt_row_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_provider_command_runtime_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_provider_command_runtime_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_PROVIDER_COMMAND_RUNTIME_BUILT"
REQUEST_MATRIX_STATUS = "SOURCE_ADAPTER_PROVIDER_COMMAND_REQUEST_MATRIX_READY"
RECEIPT_BATCH_STATUS = "SOURCE_ADAPTER_PROVIDER_COMMAND_EXECUTION_RECEIPTS_READY"
HANDOFF_STATUS = "SOURCE_ADAPTER_PROVIDER_COMMAND_RUNTIME_READY_FOR_NAMED_SITE_SMOKE_EXECUTION"
BLOCKED_STATUS = "SOURCE_ADAPTER_PROVIDER_COMMAND_RUNTIME_NEEDS_REVIEW"

COMMAND_RUNTIME_ID = "source_adapter.provider_command_runtime.subprocess_adapter"
SECRET_MARKERS = ("secret", "token", "password", "cookie", "apikey", "api_key", "authorization", "bearer")


@dataclass(frozen=True)
class SourceAdapterProviderCommandRuntime:
    package: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def short_hash(value: Any, length: int = 12) -> str:
    return sha256_text(value)[:length]


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{short_hash(value)}"


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key) or []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _operator_execution_rows(runtime_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(runtime_package, "source_adapter_operator_approved_execution_rows")


def _default_output_root() -> Path:
    return Path(tempfile.mkdtemp(prefix="source_adapter_provider_command_runtime_"))


def _default_command(provider_action: str) -> list[str]:
    payload = {
        "provider_action": provider_action,
        "adapter": "local_command_adapter",
        "result": "accepted",
    }
    text = json.dumps(payload, sort_keys=True)
    if os.name == "nt":
        return ["cmd", "/c", "echo", text]
    return ["/bin/sh", "-c", "printf %s\\n " + shlex.quote(text)]


def _is_secret_key(key: str) -> bool:
    folded = key.lower().replace("-", "_")
    return any(marker in folded for marker in SECRET_MARKERS)


def _redact_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in values.items():
        if _is_secret_key(str(key)):
            redacted[str(key)] = "<redacted>"
        else:
            redacted[str(key)] = value
    return redacted


def _safe_env(extra_env: Mapping[str, Any] | None = None) -> dict[str, str]:
    base = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "TEMP": os.environ.get("TEMP", tempfile.gettempdir()),
        "TMP": os.environ.get("TMP", tempfile.gettempdir()),
    }
    for key, value in (extra_env or {}).items():
        if not _is_secret_key(str(key)):
            base[str(key)] = str(value)
    return base


def _validate_runtime(runtime_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if runtime_package.get("schema_version") != OPERATOR_RUNTIME_SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_operator_runtime_schema", "severity": "error", "message": "operator approved execution runtime schema was not recognised"})
    if runtime_package.get("operator_approved_execution_runtime_status") != OPERATOR_RUNTIME_STATUS:
        issues.append({"issue_id": "operator_runtime_not_built", "severity": "error", "message": "operator approved execution runtime is not built"})
    summary = runtime_package.get("operator_summary") or {}
    if isinstance(summary, Mapping) and summary.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved"})
    if len(_operator_execution_rows(runtime_package)) != 5:
        issues.append({"issue_id": "unexpected_operator_execution_row_count", "severity": "error", "message": "expected five operator-approved execution rows"})
    return issues


def _command_for_action(action: str, action_commands: Mapping[str, Sequence[str]] | None) -> list[str]:
    configured = (action_commands or {}).get(action)
    if configured:
        return [str(part) for part in configured]
    return _default_command(action)


def build_provider_command_request_matrix(
    runtime_package: Mapping[str, Any],
    *,
    action_commands: Mapping[str, Sequence[str]] | None = None,
    output_root: str | Path | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    output_path = Path(output_root) if output_root is not None else _default_output_root()
    rows: list[dict[str, Any]] = []
    for execution_row in _operator_execution_rows(runtime_package):
        execution_id = str(execution_row.get("operator_approved_execution_row_id") or stable_id("source_adapter.operator_execution", execution_row))
        named_site_id = str(execution_row.get("named_site_id") or f"named_site_{len(rows)}")
        site_output_dir = output_path / named_site_id
        credential_reference_id = str(execution_row.get("credential_reference_id") or f"keys_accounts://operator/{execution_row.get('adapter_id')}/credential_reference")
        for action in PROVIDER_ACTIONS:
            command = _command_for_action(action, action_commands)
            payload = {
                "source_operator_approved_execution_row_id": execution_id,
                "provider_action": action,
                "named_site_id": named_site_id,
                "adapter_id": execution_row.get("adapter_id"),
                "source_kind": execution_row.get("source_kind"),
                "source_url_or_local_fixture_ref": execution_row.get("source_url_or_local_fixture_ref"),
                "capture_profile": execution_row.get("capture_profile"),
                "credential_reference_id": credential_reference_id if action == "credential_lookup" else None,
                "redacted_credential_reference_hash": hashlib.sha256(credential_reference_id.encode("utf-8")).hexdigest() if action == "credential_lookup" else None,
            }
            rows.append({
                "schema_version": REQUEST_SCHEMA_VERSION,
                "row_index": len(rows),
                "provider_command_request_id": stable_id("source_adapter.provider_command_request", {"execution": execution_id, "action": action}),
                "source_operator_approved_execution_row_id": execution_id,
                "provider_action": action,
                "command_runtime_id": COMMAND_RUNTIME_ID,
                "command": command,
                "cwd": str(site_output_dir),
                "timeout_seconds": int(timeout_seconds),
                "request_payload": payload,
                "request_payload_sha256": sha256_text(payload),
                "operator_approved": bool(execution_row.get("operator_approved", True)),
                "receipt_required": True,
                "provider_specific_command_configured": action in (action_commands or {}),
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            })
    return {
        "schema_version": REQUEST_MATRIX_SCHEMA_VERSION,
        "provider_command_request_matrix_status": REQUEST_MATRIX_STATUS,
        "provider_command_request_row_count": len(rows),
        "operator_execution_row_count": len(_operator_execution_rows(runtime_package)),
        "provider_action_count": len(PROVIDER_ACTIONS),
        "command_runtime_id": COMMAND_RUNTIME_ID,
        "output_root": str(output_path),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "provider_command_request_rows": rows,
    }


def execute_provider_command_request(row: Mapping[str, Any], *, extra_env: Mapping[str, Any] | None = None) -> dict[str, Any]:
    command = [str(part) for part in (row.get("command") or [])]
    if not command:
        raise ValueError("provider command request did not include a command")
    cwd = Path(str(row.get("cwd") or tempfile.mkdtemp(prefix="source_adapter_provider_command_runtime_row_")))
    cwd.mkdir(parents=True, exist_ok=True)
    timeout_seconds = int(row.get("timeout_seconds") or 30)
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=_safe_env(extra_env),
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    payload = dict(row.get("request_payload") or {})
    receipt_payload = {
        "schema_version": "source_adapter_provider_command_execution_receipt_payload_v1",
        "provider_action": row.get("provider_action"),
        "command_runtime_id": COMMAND_RUNTIME_ID,
        "command": command,
        "cwd": str(cwd),
        "returncode": completed.returncode,
        "stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr.encode("utf-8")).hexdigest(),
        "stdout_preview": stdout[:500],
        "stderr_preview": stderr[:500],
        "request_payload_sha256": row.get("request_payload_sha256"),
        "named_site_id": payload.get("named_site_id"),
        "adapter_id": payload.get("adapter_id"),
        "source_kind": payload.get("source_kind"),
        "credential_reference_present": bool(payload.get("credential_reference_id")),
        "redacted_credential_reference_hash": payload.get("redacted_credential_reference_hash"),
        "raw_credential_material_stored": False,
        "extra_env_redacted": _redact_mapping(extra_env or {}),
    }
    receipt_path = cwd / f"{row.get('provider_action')}_command_execution_receipt.json"
    receipt_path.write_text(json.dumps(receipt_payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "row_index": int(row.get("row_index", 0)),
        "provider_command_execution_receipt_id": stable_id("source_adapter.provider_command_execution_receipt", receipt_payload),
        "source_provider_command_request_id": row.get("provider_command_request_id"),
        "source_operator_approved_execution_row_id": row.get("source_operator_approved_execution_row_id"),
        "provider_action": row.get("provider_action"),
        "named_site_id": payload.get("named_site_id"),
        "command_runtime_id": COMMAND_RUNTIME_ID,
        "command_execution_performed": True,
        "returncode": completed.returncode,
        "execution_succeeded": completed.returncode == 0,
        "receipt_path": str(receipt_path),
        "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "stdout_sha256": receipt_payload["stdout_sha256"],
        "stderr_sha256": receipt_payload["stderr_sha256"],
        "raw_credential_material_stored": False,
        "redacted_credential_reference_hash": payload.get("redacted_credential_reference_hash"),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }


def _execute_request_matrix(matrix: Mapping[str, Any], *, extra_env: Mapping[str, Any] | None = None) -> dict[str, Any]:
    receipts = [execute_provider_command_request(row, extra_env=extra_env) for row in _rows(matrix, "provider_command_request_rows")]
    return {
        "schema_version": RECEIPT_BATCH_SCHEMA_VERSION,
        "provider_command_execution_receipt_batch_status": RECEIPT_BATCH_STATUS if all(row.get("execution_succeeded") for row in receipts) else "SOURCE_ADAPTER_PROVIDER_COMMAND_EXECUTION_RECEIPTS_NEED_REVIEW",
        "provider_command_execution_receipt_row_count": len(receipts),
        "successful_execution_count": sum(1 for row in receipts if row.get("execution_succeeded")),
        "failed_execution_count": sum(1 for row in receipts if not row.get("execution_succeeded")),
        "command_runtime_id": COMMAND_RUNTIME_ID,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "provider_command_execution_receipt_rows": receipts,
    }


def build_source_adapter_provider_command_runtime(
    runtime_package: Mapping[str, Any] | None = None,
    *,
    action_commands: Mapping[str, Sequence[str]] | None = None,
    output_root: str | Path | None = None,
    extra_env: Mapping[str, Any] | None = None,
    timeout_seconds: int = 30,
    operator_id: str = "operator",
    execution_notes: Sequence[str] | None = None,
) -> SourceAdapterProviderCommandRuntime:
    runtime_package = runtime_package or example_operator_approved_execution_runtime_package()
    issues = _validate_runtime(runtime_package)
    request_matrix = build_provider_command_request_matrix(
        runtime_package,
        action_commands=action_commands,
        output_root=output_root,
        timeout_seconds=timeout_seconds,
    )
    receipt_batch = _execute_request_matrix(request_matrix, extra_env=extra_env) if not issues else {
        "schema_version": RECEIPT_BATCH_SCHEMA_VERSION,
        "provider_command_execution_receipt_batch_status": "SOURCE_ADAPTER_PROVIDER_COMMAND_EXECUTION_RECEIPTS_NOT_RUN_DUE_TO_INPUT_ERRORS",
        "provider_command_execution_receipt_row_count": 0,
        "provider_command_execution_receipt_rows": [],
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }
    if int(receipt_batch.get("failed_execution_count", 0) or 0):
        issues.append({"issue_id": "provider_command_execution_failed", "severity": "error", "message": "one or more provider commands returned a non-zero exit code"})
    handoff = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if not issues else BLOCKED_STATUS,
        "provider_command_request_row_count": request_matrix.get("provider_command_request_row_count"),
        "provider_command_execution_receipt_row_count": receipt_batch.get("provider_command_execution_receipt_row_count"),
        "successful_execution_count": receipt_batch.get("successful_execution_count", 0),
        "real_provider_command_templates_supported": True,
        "named_site_smoke_execution_ready": not issues,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": STATUS if not issues else BLOCKED_STATUS,
        "operator_id": operator_id,
        "provider_command_request_row_count": request_matrix.get("provider_command_request_row_count"),
        "provider_command_execution_receipt_row_count": receipt_batch.get("provider_command_execution_receipt_row_count"),
        "successful_execution_count": receipt_batch.get("successful_execution_count", 0),
        "failed_execution_count": receipt_batch.get("failed_execution_count", 0),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "next_actions": [
            "Wire provider command runtime into named-site smoke execution.",
            "Replace default local commands with provider-specific browser/archive/release/library command adapters when configured.",
            "Keep KEYS/ACCOUNTS references redacted in command receipts.",
        ],
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "provider_command_runtime_status": STATUS if not issues else BLOCKED_STATUS,
        "source_operator_approved_execution_runtime_id": runtime_package.get("source_adapter_operator_approved_execution_runtime_id"),
        "command_runtime_id": COMMAND_RUNTIME_ID,
        "operator_id": operator_id,
        "execution_notes": list(execution_notes or []),
        "issue_count": len(issues),
        "issues": list(issues),
        "source_adapter_provider_command_request_matrix": request_matrix,
        "source_adapter_provider_command_execution_receipt_batch": receipt_batch,
        "source_adapter_provider_command_runtime_handoff": handoff,
        "operator_summary": operator_summary,
    }
    package["source_adapter_provider_command_runtime_id"] = stable_id("source_adapter.provider_command_runtime", package)
    return SourceAdapterProviderCommandRuntime(package)


def example_provider_command_runtime_package() -> dict[str, Any]:
    output_root = _default_output_root()
    return build_source_adapter_provider_command_runtime(
        output_root=output_root,
        extra_env={"EXAMPLE_SECRET_TOKEN": "hidden-token-value", "VISIBLE_FLAG": "1"},
        operator_id="example_operator",
        execution_notes=["deterministic provider command runtime example"],
    ).as_dict()


if __name__ == "__main__":
    print(json.dumps(example_provider_command_runtime_package(), indent=2, sort_keys=True))
