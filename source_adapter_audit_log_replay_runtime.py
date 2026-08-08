from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "source_adapter_audit_log_replay_runtime_v1"
ROW_SCHEMA_VERSION = "source_adapter_audit_log_replay_runtime_v1_row_v1"
STATUS = "SOURCE_ADAPTER_AUDIT_LOG_REPLAY_RUNTIME_BUILT"
KEYS_ACCOUNTS_LABEL = "KEYS/ACCOUNTS"
CAPABILITY_IDS = ['operator_event', 'provider_event', 'receipt_event', 'release_event']


@dataclass(frozen=True)
class AuditLogReplayRuntimeRow:
    row_id: str
    row_index: int
    capability_id: str
    runtime_status: str
    execution_mode: str
    provider_call_supported: bool
    receipt_required: bool
    keys_accounts_label: str
    secret_material_present: bool
    redacted_reference_hash: str
    source_artifact_role: str
    schema_version: str = ROW_SCHEMA_VERSION


@dataclass(frozen=True)
class AuditLogReplayRuntimePackage:
    schema_version: str
    package_id: str
    status: str
    purpose: str
    row_count: int
    rows: list[dict[str, Any]]
    keys_accounts_label: str
    issue_count: int
    issues: list[str]
    verification: dict[str, Any]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_id(prefix: str, payload: Any) -> str:
    return f"{prefix}.{_sha256_text(_canonical_json(payload))[:12]}"


def _redacted_reference_hash(capability_id: str, row_index: int) -> str:
    # This deliberately hashes only a reference label. Secret material never enters
    # package rows, receipts, CLI output, or tests.
    return _sha256_text(f"{KEYS_ACCOUNTS_LABEL}:{capability_id}:{row_index}")[:24]


def build_rows(*, execution_mode: str = "operator_controlled") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, capability_id in enumerate(CAPABILITY_IDS):
        seed = {
            "schema_version": ROW_SCHEMA_VERSION,
            "capability_id": capability_id,
            "row_index": index,
            "execution_mode": execution_mode,
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        }
        row = AuditLogReplayRuntimeRow(
            row_id=_stable_id("source_adapter.audit_log_replay_runtime.row", seed),
            row_index=index,
            capability_id=capability_id,
            runtime_status=STATUS,
            execution_mode=execution_mode,
            provider_call_supported=True,
            receipt_required=True,
            keys_accounts_label=KEYS_ACCOUNTS_LABEL,
            secret_material_present=False,
            redacted_reference_hash=_redacted_reference_hash(capability_id, index),
            source_artifact_role="audit log replay",
        )
        rows.append(asdict(row))
    return rows


def verify_package(package: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    rows = list(package.get("rows", []))
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append("schema_version_mismatch")
    if package.get("status") != STATUS:
        issues.append("status_mismatch")
    if package.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append("keys_accounts_label_mismatch")
    if package.get("row_count") != len(rows):
        issues.append("row_count_mismatch")
    if len(rows) != len(CAPABILITY_IDS):
        issues.append("capability_row_count_mismatch")
    for row in rows:
        if row.get("secret_material_present"):
            issues.append(f"secret_material_present:{row.get('row_id')}")
        if not row.get("redacted_reference_hash"):
            issues.append(f"missing_redacted_reference_hash:{row.get('row_id')}")
        if not row.get("receipt_required"):
            issues.append(f"receipt_not_required:{row.get('row_id')}")
        if row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
            issues.append(f"row_keys_accounts_label_mismatch:{row.get('row_id')}")
    return {
        "schema_version": f"{SCHEMA_VERSION}_verifier_v1",
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "row_count": len(rows),
        "status": package.get("status"),
        "keys_accounts_label": package.get("keys_accounts_label"),
    }


def build_package(*, operator_id: str = "operator", execution_mode: str = "operator_controlled") -> dict[str, Any]:
    rows = build_rows(execution_mode=execution_mode)
    package_seed = {
        "schema_version": SCHEMA_VERSION,
        "operator_id": operator_id,
        "row_ids": [row["row_id"] for row in rows],
        "purpose": "audit log replay",
    }
    package: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "package_id": _stable_id("source_adapter.audit_log_replay_runtime.package", package_seed),
        "status": STATUS,
        "purpose": "audit log replay",
        "operator_id": operator_id,
        "execution_mode": execution_mode,
        "row_count": len(rows),
        "rows": rows,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "secret_material_present": False,
        "implementation_notes": [
            "runtime rows are executable by downstream provider adapters",
            "provider receipts are required for every row",
            "KEYS/ACCOUNTS references are represented only by redacted hashes",
        ],
    }
    package["verification"] = verify_package(package)
    package["issue_count"] = package["verification"]["issue_count"]
    package["issues"] = package["verification"]["issues"]
    return package


def write_package(output_dir: str | Path, *, operator_id: str = "operator") -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    package = build_package(operator_id=operator_id)
    package_path = out / f"{package['package_id']}.audit_log_replay_runtime.json"
    rows_path = out / f"{package['package_id']}.audit_log_replay_runtime.rows.json"
    verification_path = out / f"{package['package_id']}.audit_log_replay_runtime.verification.json"
    package_path.write_text(json.dumps(package, indent=2, sort_keys=True), encoding="utf-8")
    rows_path.write_text(json.dumps(package["rows"], indent=2, sort_keys=True), encoding="utf-8")
    verification_path.write_text(json.dumps(package["verification"], indent=2, sort_keys=True), encoding="utf-8")
    stored_files = []
    for role, path in [
        ("package", package_path),
        ("rows", rows_path),
        ("verification", verification_path),
    ]:
        content = path.read_text(encoding="utf-8")
        stored_files.append({
            "role": role,
            "path": str(path),
            "filename": path.name,
            "byte_count": len(content.encode("utf-8")),
            "sha256": _sha256_text(content),
        })
    return {
        "schema_version": f"{SCHEMA_VERSION}_store_v1",
        "store_status": "STORED",
        "package_id": package["package_id"],
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": package["verification"],
    }


__all__ = [
    "SCHEMA_VERSION",
    "ROW_SCHEMA_VERSION",
    "STATUS",
    "KEYS_ACCOUNTS_LABEL",
    "CAPABILITY_IDS",
    "build_rows",
    "build_package",
    "verify_package",
    "write_package",
]
