"""Batch preview reconciliation after reviewed Profile/Media folder operations.

V76I closes the loop created by V76G.  Reviewed folder operations can rename or
move folders under the database root, while the explicit batch JSON selected by
Database mode may still describe the old source title/bucket.  This module builds
a read-only reconciliation plan and can write a new standalone batch-preview JSON
only when the caller supplies the exact confirmation phrase.

It does not scan folders, create folders, move folders, rename folders, copy
media, download media, classify automatically, or infer sensitive identifiers.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_database import stable_profile_id, utc_now_iso

PROFILE_MEDIA_DATABASE_RECONCILIATION_SCHEMA_VERSION = "profile-media-batch-reconciliation-v76i"
PROFILE_MEDIA_DATABASE_RECONCILIATION_WRITE_CONFIRMATION = "WRITE_RECONCILED_PROFILE_MEDIA_BATCH_PREVIEW"


@dataclass(frozen=True)
class ProfileMediaBatchReconciliationChange:
    """One source/profile batch field change proposed after reviewed operations."""

    change_id: str
    item_type: str
    item_index: int
    field_name: str
    old_value: str
    new_value: str
    reason: str
    operation_id: str = ""
    schema_version: str = PROFILE_MEDIA_DATABASE_RECONCILIATION_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaBatchReconciliationPlan:
    """Read-only plan for a reconciled batch-preview JSON."""

    source_batch_json: str
    operations_json: str = ""
    output_batch_json: str = ""
    original_payload: Mapping[str, Any] = field(default_factory=dict)
    reconciled_payload: Mapping[str, Any] = field(default_factory=dict)
    changes: tuple[ProfileMediaBatchReconciliationChange, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_DATABASE_RECONCILIATION_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["changes"] = [change.to_dict() for change in self.changes]
        data["change_count"] = len(self.changes)
        data["warning_count"] = len(self.warnings)
        return data


@dataclass(frozen=True)
class ProfileMediaBatchReconciliationWriteResult:
    """Result of guarded reconciled batch-preview write."""

    status: str
    plan: ProfileMediaBatchReconciliationPlan
    output_batch_json: str = ""
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_DATABASE_RECONCILIATION_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["plan"] = self.plan.to_dict()
        data["warning_count"] = len(self.warnings)
        return data


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("JSON root must be an object")
    return payload


def _normalize_path(value: object) -> str:
    text = str(value or "").strip().replace("\\", "/")
    while "//" in text:
        text = text.replace("//", "/")
    return text.strip("/")


def _basename(path: object) -> str:
    text = _normalize_path(path)
    if not text:
        return ""
    return text.split("/")[-1]


def _bucket_from_path(path: object) -> str:
    parts = [part for part in _normalize_path(path).split("/") if part]
    if "Sources" not in parts:
        return ""
    idx = parts.index("Sources")
    after = parts[idx + 1 :]
    if not after:
        return ""
    if len(after) >= 3 and after[0] == "Social Media" and after[1] in {"Online", "Offline"}:
        return f"Social Media/{after[1]}"
    if after[0] == "Internal Media":
        return "Internal Media"
    if after[0] == "Articles":
        return "Articles"
    return after[0]


def _operations_from_payload(payload: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    if isinstance(payload.get("operations"), list):
        return tuple(dict(item) for item in payload["operations"] if isinstance(item, Mapping))
    if isinstance(payload.get("operation_specs"), list):
        return tuple(dict(item) for item in payload["operation_specs"] if isinstance(item, Mapping))
    if isinstance(payload.get("plan"), Mapping) and isinstance(payload["plan"].get("operation_specs"), list):
        return tuple(dict(item) for item in payload["plan"]["operation_specs"] if isinstance(item, Mapping))
    if isinstance(payload.get("operation_results"), list):
        return tuple(dict(item) for item in payload["operation_results"] if isinstance(item, Mapping))
    return ()


def _change(item_type: str, item_index: int, field_name: str, old: object, new: object, reason: str, operation_id: str) -> ProfileMediaBatchReconciliationChange:
    return ProfileMediaBatchReconciliationChange(
        change_id="batch_reconcile_" + stable_profile_id(f"{item_type}:{item_index}:{field_name}:{old}->{new}:{operation_id}"),
        item_type=item_type,
        item_index=item_index,
        field_name=field_name,
        old_value=str(old or ""),
        new_value=str(new or ""),
        reason=reason,
        operation_id=str(operation_id or ""),
    )


def build_batch_reconciliation_plan(
    *,
    batch_payload: Mapping[str, Any] | None = None,
    batch_json_path: str | Path = "",
    operations_payload: Mapping[str, Any] | None = None,
    operations_json_path: str | Path = "",
    output_batch_json: str | Path = "",
) -> ProfileMediaBatchReconciliationPlan:
    """Build a read-only reconciliation plan from explicit batch/operation inputs."""

    warnings: list[str] = []
    if batch_payload is None:
        if not str(batch_json_path).strip():
            raise ValueError("batch_payload or batch_json_path is required")
        batch_payload = load_json(batch_json_path)
    if operations_payload is None and str(operations_json_path).strip():
        operations_payload = load_json(operations_json_path)
    operations = _operations_from_payload(operations_payload or {})
    if not operations:
        warnings.append("no_folder_operations_supplied")

    reconciled: dict[str, Any] = json.loads(json.dumps(dict(batch_payload)))
    sources = reconciled.get("sources", [])
    if not isinstance(sources, list):
        sources = []
        warnings.append("batch_sources_not_list")
    changes: list[ProfileMediaBatchReconciliationChange] = []

    for operation in operations:
        op_type = str(operation.get("operation_type") or "")
        source_path = _normalize_path(operation.get("source_path") or operation.get("source_abs") or "")
        dest_path = _normalize_path(operation.get("destination_path") or operation.get("destination_abs") or "")
        old_title = _basename(source_path)
        new_title = _basename(dest_path or operation.get("new_name"))
        new_bucket = _bucket_from_path(dest_path)
        op_id = str(operation.get("operation_id") or "")
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                continue
            current_title = str(source.get("source_title") or "")
            current_bucket = str(source.get("source_bucket") or "")
            current_address = _normalize_path(source.get("local_address") or "")
            title_matches = bool(old_title and current_title == old_title)
            address_matches = bool(source_path and current_address and current_address.endswith(source_path))
            if not (title_matches or address_matches):
                continue
            if new_title and current_title != new_title:
                changes.append(_change("source", index, "source_title", current_title, new_title, f"{op_type}_destination_title", op_id))
                source["source_title"] = new_title
            if new_bucket and current_bucket != new_bucket:
                changes.append(_change("source", index, "source_bucket", current_bucket, new_bucket, f"{op_type}_destination_bucket", op_id))
                source["source_bucket"] = new_bucket
            if current_address and dest_path and current_address.endswith(source_path):
                new_address = current_address[: -len(source_path)].rstrip("/") + "/" + dest_path
                changes.append(_change("source", index, "local_address", current_address, new_address, f"{op_type}_destination_path", op_id))
                source["local_address"] = new_address

    notes = dict(reconciled.get("planner_notes") or {}) if isinstance(reconciled.get("planner_notes"), Mapping) else {}
    notes.update({
        "reconciled_after_reviewed_folder_operations": True,
        "reconciliation_schema_version": PROFILE_MEDIA_DATABASE_RECONCILIATION_SCHEMA_VERSION,
        "reconciliation_change_count": len(changes),
    })
    reconciled["planner_notes"] = notes

    return ProfileMediaBatchReconciliationPlan(
        source_batch_json=str(batch_json_path or ""),
        operations_json=str(operations_json_path or ""),
        output_batch_json=str(output_batch_json or ""),
        original_payload=dict(batch_payload),
        reconciled_payload=reconciled,
        changes=tuple(changes),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def write_reconciled_batch_preview_if_confirmed(
    plan: ProfileMediaBatchReconciliationPlan,
    output_batch_json: str | Path = "",
    *,
    confirmation_phrase: str = "",
) -> ProfileMediaBatchReconciliationWriteResult:
    """Write the reconciled batch preview only after exact confirmation."""

    out = str(output_batch_json or plan.output_batch_json or "")
    warnings: list[str] = list(plan.warnings)
    if confirmation_phrase != PROFILE_MEDIA_DATABASE_RECONCILIATION_WRITE_CONFIRMATION:
        warnings.append("confirmation_required_for_reconciled_batch_write")
        return ProfileMediaBatchReconciliationWriteResult(
            status="blocked_confirmation_required",
            plan=plan,
            output_batch_json=out,
            warnings=tuple(dict.fromkeys(warnings)),
        )
    if not out:
        warnings.append("output_batch_json_required")
        return ProfileMediaBatchReconciliationWriteResult(
            status="blocked_output_path_required",
            plan=plan,
            output_batch_json=out,
            warnings=tuple(dict.fromkeys(warnings)),
        )
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan.reconciled_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return ProfileMediaBatchReconciliationWriteResult(
        status="reconciled_batch_preview_written",
        plan=plan,
        output_batch_json=str(path),
        warnings=tuple(dict.fromkeys(warnings)),
        file_write_performed=True,
    )


def render_batch_reconciliation_plan_text(plan: ProfileMediaBatchReconciliationPlan) -> str:
    lines = [
        "Profile/Media Batch Reconciliation Plan",
        f"Status: {'changes_ready' if plan.changes else 'no_changes'}",
        f"Source batch JSON: {plan.source_batch_json or '(payload supplied)'}",
        f"Operations JSON: {plan.operations_json or '(payload supplied)'}",
        f"Output batch JSON: {plan.output_batch_json or '(not configured)'}",
        f"Changes: {len(plan.changes)}",
        f"Folder scan performed: {plan.folder_scan_performed}",
        f"Folder creation performed: {plan.folder_creation_performed}",
        f"Folder move performed: {plan.folder_move_performed}",
        f"Folder rename performed: {plan.folder_rename_performed}",
        f"File copy performed: {plan.file_copy_performed}",
        f"File write performed: {plan.file_write_performed}",
        f"Media download performed: {plan.media_download_performed}",
        f"Automatic classification performed: {plan.automatic_classification_performed}",
        f"Sensitive identifier inference performed: {plan.sensitive_identifier_inference_performed}",
        "",
        "Changes:",
    ]
    if not plan.changes:
        lines.append("- none")
    for change in plan.changes[:60]:
        lines.append(f"- {change.item_type}[{change.item_index}].{change.field_name}: {change.old_value} -> {change.new_value}")
    if len(plan.changes) > 60:
        lines.append(f"- ... {len(plan.changes) - 60} more")
    if plan.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in plan.warnings[:40]:
            lines.append(f"- {warning}")
    return "\n".join(lines)


def reconciliation_payload(plan: ProfileMediaBatchReconciliationPlan) -> dict[str, Any]:
    return plan.to_dict()
