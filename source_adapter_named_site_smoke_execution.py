from __future__ import annotations

import hashlib
import json
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from source_adapter_operator_approved_execution_runtime import (
    KEYS_ACCOUNTS_LABEL,
    PROVIDER_ACTIONS,
    example_operator_approved_execution_runtime_package,
)
from source_adapter_provider_command_runtime import (
    HANDOFF_STATUS as PROVIDER_COMMAND_HANDOFF_STATUS,
    build_source_adapter_provider_command_runtime,
    example_provider_command_runtime_package,
)

SCHEMA_VERSION = "source_adapter_named_site_smoke_execution_v1"
MATRIX_SCHEMA_VERSION = "source_adapter_named_site_smoke_execution_matrix_v1"
SITE_ROW_SCHEMA_VERSION = "source_adapter_named_site_smoke_execution_site_row_v1"
ACTION_RECEIPT_BATCH_SCHEMA_VERSION = "source_adapter_named_site_provider_action_receipt_batch_v1"
ACTION_RECEIPT_SCHEMA_VERSION = "source_adapter_named_site_provider_action_receipt_row_v1"
MANIFEST_SCHEMA_VERSION = "source_adapter_named_site_smoke_execution_manifest_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_named_site_smoke_execution_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_named_site_smoke_execution_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_NAMED_SITE_SMOKE_EXECUTION_BUILT"
MATRIX_STATUS = "SOURCE_ADAPTER_NAMED_SITE_SMOKE_EXECUTION_MATRIX_READY"
ACTION_RECEIPT_BATCH_STATUS = "SOURCE_ADAPTER_NAMED_SITE_PROVIDER_ACTION_RECEIPTS_READY"
MANIFEST_STATUS = "SOURCE_ADAPTER_NAMED_SITE_SMOKE_EXECUTION_MANIFEST_READY"
HANDOFF_STATUS = "SOURCE_ADAPTER_NAMED_SITE_SMOKE_EXECUTION_READY_FOR_RECEIPT_REVIEW"
BLOCKED_STATUS = "SOURCE_ADAPTER_NAMED_SITE_SMOKE_EXECUTION_NEEDS_REVIEW"


@dataclass(frozen=True)
class SourceAdapterNamedSiteSmokeExecution:
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


def _provider_command_receipt_rows(provider_command_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    batch = provider_command_package.get("source_adapter_provider_command_execution_receipt_batch") or {}
    if not isinstance(batch, Mapping):
        return []
    return _rows(batch, "provider_command_execution_receipt_rows")


def _validate_inputs(operator_runtime_package: Mapping[str, Any], provider_command_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if operator_runtime_package.get("operator_summary", {}).get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error", "message": "operator runtime did not preserve KEYS/ACCOUNTS"})
    if len(_operator_execution_rows(operator_runtime_package)) != 5:
        issues.append({"issue_id": "unexpected_operator_execution_row_count", "severity": "error", "message": "expected five named-site operator execution rows"})
    handoff = provider_command_package.get("source_adapter_provider_command_runtime_handoff") or {}
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != PROVIDER_COMMAND_HANDOFF_STATUS:
        issues.append({"issue_id": "provider_command_runtime_not_ready", "severity": "error", "message": "provider command runtime handoff was not ready"})
    if len(_provider_command_receipt_rows(provider_command_package)) != 25:
        issues.append({"issue_id": "unexpected_provider_command_receipt_count", "severity": "error", "message": "expected 25 provider command receipts"})
    return issues


def _build_execution_matrix(operator_runtime_package: Mapping[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for row in _operator_execution_rows(operator_runtime_package):
        named_site_id = str(row.get("named_site_id") or f"named_site_{len(rows)}")
        rows.append({
            "schema_version": SITE_ROW_SCHEMA_VERSION,
            "row_index": len(rows),
            "named_site_smoke_execution_site_row_id": stable_id("source_adapter.named_site_smoke_execution_site", row),
            "source_operator_approved_execution_row_id": row.get("operator_approved_execution_row_id"),
            "named_site_id": named_site_id,
            "adapter_id": row.get("adapter_id"),
            "source_kind": row.get("source_kind"),
            "fixture_family": row.get("fixture_family"),
            "source_url_or_local_fixture_ref": row.get("source_url_or_local_fixture_ref"),
            "capture_profile": row.get("capture_profile"),
            "operator_approval_id": row.get("operator_approval_id"),
            "operator_approved": bool(row.get("operator_approved", True)),
            "provider_actions": list(PROVIDER_ACTIONS),
            "provider_action_count": len(PROVIDER_ACTIONS),
            "credential_reference_id_present": bool(row.get("credential_reference_id")),
            "redacted_credential_reference_hash": row.get("redacted_credential_reference_hash"),
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            "execution_site_status": "READY_FOR_PROVIDER_ACTION_EXECUTION",
        })
    return {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "named_site_smoke_execution_matrix_status": MATRIX_STATUS,
        "named_site_execution_site_count": len(rows),
        "provider_action_count": len(PROVIDER_ACTIONS),
        "expected_provider_action_receipt_count": len(rows) * len(PROVIDER_ACTIONS),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "named_site_smoke_execution_site_rows": rows,
    }


def _build_action_receipts(matrix: Mapping[str, Any], provider_command_package: Mapping[str, Any]) -> dict[str, Any]:
    provider_rows = _provider_command_receipt_rows(provider_command_package)
    by_site_action = {(str(row.get("named_site_id")), str(row.get("provider_action"))): row for row in provider_rows}
    receipts: list[dict[str, Any]] = []
    for site_row in _rows(matrix, "named_site_smoke_execution_site_rows"):
        named_site_id = str(site_row.get("named_site_id"))
        for action in PROVIDER_ACTIONS:
            provider_row = by_site_action.get((named_site_id, action), {})
            receipts.append({
                "schema_version": ACTION_RECEIPT_SCHEMA_VERSION,
                "row_index": len(receipts),
                "named_site_provider_action_receipt_id": stable_id("source_adapter.named_site_provider_action_receipt", {"site": named_site_id, "action": action, "provider": provider_row.get("provider_command_execution_receipt_id")}),
                "source_named_site_smoke_execution_site_row_id": site_row.get("named_site_smoke_execution_site_row_id"),
                "source_provider_command_execution_receipt_id": provider_row.get("provider_command_execution_receipt_id"),
                "named_site_id": named_site_id,
                "adapter_id": site_row.get("adapter_id"),
                "source_kind": site_row.get("source_kind"),
                "provider_action": action,
                "provider_command_returncode": provider_row.get("returncode"),
                "provider_command_execution_succeeded": provider_row.get("execution_succeeded") is True,
                "provider_receipt_path": provider_row.get("receipt_path"),
                "provider_receipt_sha256": provider_row.get("receipt_sha256"),
                "action_receipt_status": "SOURCE_ADAPTER_NAMED_SITE_PROVIDER_ACTION_RECEIPT_RECORDED" if provider_row.get("execution_succeeded") is True else "SOURCE_ADAPTER_NAMED_SITE_PROVIDER_ACTION_RECEIPT_NEEDS_REVIEW",
                "redacted_credential_reference_hash": provider_row.get("redacted_credential_reference_hash") or site_row.get("redacted_credential_reference_hash"),
                "raw_credential_material_stored": False,
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            })
    success_count = sum(1 for row in receipts if row.get("provider_command_execution_succeeded"))
    return {
        "schema_version": ACTION_RECEIPT_BATCH_SCHEMA_VERSION,
        "named_site_provider_action_receipt_batch_status": ACTION_RECEIPT_BATCH_STATUS if success_count == len(receipts) else "SOURCE_ADAPTER_NAMED_SITE_PROVIDER_ACTION_RECEIPTS_NEED_REVIEW",
        "named_site_provider_action_receipt_row_count": len(receipts),
        "successful_action_receipt_count": success_count,
        "failed_action_receipt_count": len(receipts) - success_count,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "named_site_provider_action_receipt_rows": receipts,
    }


def _write_manifest(output_dir: Path, package_seed: Mapping[str, Any]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_status": MANIFEST_STATUS,
        "named_site_execution_site_count": package_seed.get("named_site_execution_site_count"),
        "named_site_provider_action_receipt_row_count": package_seed.get("named_site_provider_action_receipt_row_count"),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "package_seed_sha256": sha256_text(package_seed),
    }
    manifest_path = output_dir / "source_adapter_named_site_smoke_execution_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    manifest["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return manifest


def build_source_adapter_named_site_smoke_execution(
    operator_runtime_package: Mapping[str, Any] | None = None,
    provider_command_package: Mapping[str, Any] | None = None,
    *,
    output_dir: str | Path | None = None,
    operator_id: str = "operator",
    smoke_notes: Sequence[str] | None = None,
) -> SourceAdapterNamedSiteSmokeExecution:
    operator_runtime_package = operator_runtime_package or example_operator_approved_execution_runtime_package()
    provider_command_package = provider_command_package or build_source_adapter_provider_command_runtime(operator_runtime_package).as_dict()
    issues = _validate_inputs(operator_runtime_package, provider_command_package)
    matrix = _build_execution_matrix(operator_runtime_package)
    action_receipts = _build_action_receipts(matrix, provider_command_package)
    if action_receipts.get("failed_action_receipt_count"):
        issues.append({"issue_id": "provider_action_receipts_failed", "severity": "error", "message": "one or more named-site provider action receipts failed"})
    output_path = Path(output_dir) if output_dir is not None else Path(tempfile.mkdtemp(prefix="source_adapter_named_site_smoke_execution_"))
    manifest_seed = {
        "named_site_execution_site_count": matrix.get("named_site_execution_site_count"),
        "named_site_provider_action_receipt_row_count": action_receipts.get("named_site_provider_action_receipt_row_count"),
        "provider_command_runtime_id": provider_command_package.get("source_adapter_provider_command_runtime_id"),
    }
    manifest = _write_manifest(output_path, manifest_seed)
    handoff = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if not issues else BLOCKED_STATUS,
        "named_site_execution_site_count": matrix.get("named_site_execution_site_count"),
        "named_site_provider_action_receipt_row_count": action_receipts.get("named_site_provider_action_receipt_row_count"),
        "provider_command_runtime_id": provider_command_package.get("source_adapter_provider_command_runtime_id"),
        "receipt_review_ready": not issues,
        "manifest_path": manifest.get("manifest_path"),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": STATUS if not issues else BLOCKED_STATUS,
        "operator_id": operator_id,
        "named_site_execution_site_count": matrix.get("named_site_execution_site_count"),
        "named_site_provider_action_receipt_row_count": action_receipts.get("named_site_provider_action_receipt_row_count"),
        "successful_action_receipt_count": action_receipts.get("successful_action_receipt_count"),
        "failed_action_receipt_count": action_receipts.get("failed_action_receipt_count"),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "next_actions": [
            "Review named-site provider action receipts.",
            "Wire GUI live-smoke button and controller dispatch to this execution package.",
            "Promote reviewed receipts into source evidence review and release/export surfaces.",
        ],
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "named_site_smoke_execution_status": STATUS if not issues else BLOCKED_STATUS,
        "source_operator_approved_execution_runtime_id": operator_runtime_package.get("source_adapter_operator_approved_execution_runtime_id"),
        "source_provider_command_runtime_id": provider_command_package.get("source_adapter_provider_command_runtime_id"),
        "operator_id": operator_id,
        "smoke_notes": list(smoke_notes or []),
        "issue_count": len(issues),
        "issues": list(issues),
        "source_adapter_named_site_smoke_execution_matrix": matrix,
        "source_adapter_named_site_provider_action_receipt_batch": action_receipts,
        "source_adapter_named_site_smoke_execution_manifest": manifest,
        "source_adapter_named_site_smoke_execution_handoff": handoff,
        "operator_summary": operator_summary,
    }
    package["source_adapter_named_site_smoke_execution_id"] = stable_id("source_adapter.named_site_smoke_execution", package)
    return SourceAdapterNamedSiteSmokeExecution(package)


def example_named_site_smoke_execution_package() -> dict[str, Any]:
    operator_runtime = example_operator_approved_execution_runtime_package()
    provider_runtime = example_provider_command_runtime_package()
    return build_source_adapter_named_site_smoke_execution(
        operator_runtime,
        provider_runtime,
        operator_id="example_operator",
        smoke_notes=["deterministic named-site smoke execution example"],
    ).as_dict()


if __name__ == "__main__":
    print(json.dumps(example_named_site_smoke_execution_package(), indent=2, sort_keys=True))
