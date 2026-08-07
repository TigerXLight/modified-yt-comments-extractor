from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "source_archive_handoff_v1"
PROVIDER_TASKS_SCHEMA_VERSION = "source_archive_provider_tasks_v1"
RESULT_TEMPLATES_SCHEMA_VERSION = "source_archive_result_templates_v1"
RESULT_INTAKE_HANDOFF_SCHEMA_VERSION = "source_archive_result_intake_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_archive_handoff_operator_summary_v1"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_DEFAULT_PROVIDERS: tuple[str, ...] = (
    "archive_today",
    "ghostarchive",
    "wayback_machine",
    "perma_cc",
    "local_mirror",
)
_PROVIDER_LABELS = {
    "archive_today": "archive.today / archive.ph",
    "ghostarchive": "Ghostarchive",
    "wayback_machine": "Wayback Machine",
    "perma_cc": "Perma.cc",
    "local_mirror": "Local mirror",
}


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _stable_hash(data: Mapping[str, Any], *, length: int = 12) -> str:
    return hashlib.sha256(_json_bytes(data)).hexdigest()[:length]


def _clean_identifier(value: object, *, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    text = _SAFE_ID_RE.sub(".", text).strip("._-")
    return text or fallback


def _coerce_mapping(value: Mapping[str, Any] | None, *, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a JSON object")
    return dict(value)


def _safe_basename(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "/" in text or "\\" in text or re.match(r"^[a-zA-Z]:", text):
        raise ValueError("archive handoff filenames must be safe basenames, not paths")
    return text


def _normalise_artifacts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    artifacts: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        filename = _safe_basename(item.get("filename") or item.get("basename") or item.get("safe_basename"))
        if not filename:
            continue
        artifacts.append(
            {
                "role": _clean_identifier(item.get("role") or item.get("artifact_role"), fallback="artifact"),
                "filename": filename,
                "sha256": str(item.get("sha256") or "").strip(),
                "byte_count": item.get("byte_count") if isinstance(item.get("byte_count"), int) and item.get("byte_count") >= 0 else 0,
                "source_stage": _clean_identifier(item.get("source_stage") or item.get("input_stage"), fallback="source_release_audit"),
            }
        )
    artifacts.sort(key=lambda entry: (entry["role"], entry["filename"]))
    return artifacts


def _normalise_notes(*note_sources: Iterable[str] | None) -> list[str]:
    notes: list[str] = []
    seen: set[str] = set()
    for source in note_sources:
        if not source:
            continue
        for note in source:
            text = str(note or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            notes.append(text)
    return notes


def _normalise_providers(providers: Sequence[str] | None) -> list[str]:
    source = providers or _DEFAULT_PROVIDERS
    normalised: list[str] = []
    seen: set[str] = set()
    for provider in source:
        provider_id = _clean_identifier(provider, fallback="archive_provider")
        if not provider_id:
            continue
        if provider_id in seen:
            continue
        seen.add(provider_id)
        normalised.append(provider_id)
    if not normalised:
        raise ValueError("at least one archive provider is required")
    return normalised


@dataclass(frozen=True)
class SourceArchiveHandoffOutputs:
    archive_handoff_package: dict[str, Any]
    provider_tasks: dict[str, Any]
    result_templates: dict[str, Any]
    result_intake_handoff: dict[str, Any]
    operator_summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "archive_handoff_package": self.archive_handoff_package,
            "provider_tasks": self.provider_tasks,
            "result_templates": self.result_templates,
            "result_intake_handoff": self.result_intake_handoff,
            "operator_summary": self.operator_summary,
        }


def build_source_archive_handoff(
    *,
    release_audit_report: Mapping[str, Any],
    traceability_map: Mapping[str, Any] | None = None,
    release_archive_handoff: Mapping[str, Any] | None = None,
    archive_providers: Sequence[str] | None = None,
    operator_id: str = "manual_archive_operator",
    handoff_notes: Iterable[str] | None = None,
) -> SourceArchiveHandoffOutputs:
    report = _coerce_mapping(release_audit_report, name="release_audit_report")
    traceability = _coerce_mapping(traceability_map, name="traceability_map")
    prior_handoff = _coerce_mapping(release_archive_handoff, name="release_archive_handoff")

    if report.get("schema_version") != "source_release_audit_v1":
        raise ValueError("release_audit_report schema_version must be source_release_audit_v1")
    if report.get("audit_status") != "READY_FOR_ARCHIVE_HANDOFF":
        raise ValueError("release_audit_report.audit_status must be READY_FOR_ARCHIVE_HANDOFF")

    release_audit_id = _clean_identifier(report.get("release_audit_id"), fallback="source.release_audit")
    release_index_id = _clean_identifier(report.get("release_index_id"), fallback="source.release_index")
    approved_release_id = _clean_identifier(report.get("approved_release_id"), fallback="source.approved_release")
    evidence_review_package_id = _clean_identifier(report.get("evidence_review_package_id"), fallback="source.evidence_review")
    queue_item_id = _clean_identifier(report.get("queue_item_id"), fallback="source.evidence_queue")
    total_export_package_id = _clean_identifier(report.get("total_export_package_id"), fallback="source.total_export_package")
    capture_bundle_id = _clean_identifier(report.get("capture_bundle_id"), fallback="source.capture_bundle")
    adapter = _clean_identifier(report.get("adapter_id"), fallback="source")
    source_url = str(report.get("source_url") or "").strip()
    if not source_url:
        raise ValueError("release_audit_report.source_url is required")

    artifacts = _normalise_artifacts(report.get("artifact_index"))
    if not artifacts:
        raise ValueError("archive handoff requires a non-empty release_audit_report.artifact_index")

    if traceability:
        if traceability.get("schema_version") != "source_release_traceability_map_v1":
            raise ValueError("traceability_map schema_version must be source_release_traceability_map_v1")
        if str(traceability.get("release_audit_id") or "") != release_audit_id:
            raise ValueError("traceability_map.release_audit_id mismatch")
        if traceability.get("traceability_status") != "READY_FOR_ARCHIVE_HANDOFF":
            raise ValueError("traceability_map must be READY_FOR_ARCHIVE_HANDOFF")

    if prior_handoff:
        if prior_handoff.get("schema_version") != "source_release_archive_handoff_v1":
            raise ValueError("release_archive_handoff schema_version mismatch")
        if str(prior_handoff.get("release_audit_id") or "") != release_audit_id:
            raise ValueError("release_archive_handoff.release_audit_id mismatch")
        if prior_handoff.get("handoff_status") != "READY_FOR_ARCHIVE_HANDOFF":
            raise ValueError("release_archive_handoff must be READY_FOR_ARCHIVE_HANDOFF")
        if prior_handoff.get("archive_submission_started") is True:
            raise ValueError("release_archive_handoff must not already mark archive submission started")

    providers = _normalise_providers(archive_providers)
    operator = _clean_identifier(operator_id, fallback="manual_archive_operator")
    audit_fingerprint = str(report.get("audit_fingerprint") or "")
    archive_handoff_seed = {
        "release_audit_id": release_audit_id,
        "release_index_id": release_index_id,
        "approved_release_id": approved_release_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "providers": providers,
        "audit_fingerprint": audit_fingerprint,
    }
    archive_handoff_id = f"{adapter}.archive_handoff.{_stable_hash(archive_handoff_seed)}"

    archive_tasks: list[dict[str, Any]] = []
    templates: list[dict[str, Any]] = []
    for provider_id in providers:
        label = _PROVIDER_LABELS.get(provider_id, provider_id.replace("_", " ").title())
        task_id = f"{archive_handoff_id}.{provider_id}.task"
        template_filename = _safe_basename(f"{archive_handoff_id}.{provider_id}.archive_result_template.json")
        archive_tasks.append(
            {
                "task_id": task_id,
                "provider_id": provider_id,
                "provider_label": label,
                "task_status": "PENDING_OPERATOR_ACTION",
                "operator_action": "MANUAL_SUBMIT_OR_RECORD",
                "source_url": source_url,
                "approval_required_before_submission": True,
                "archive_submission_started": False,
                "manual_or_live_actions_started": False,
                "result_template_filename": template_filename,
                "instructions": [
                    "Use the named provider manually only after explicit operator approval.",
                    "Paste or save the resulting archive URL/receipt into the matching result template.",
                    "Do not let this package mark the archive as complete until result intake verifies the operator-supplied result.",
                ],
            }
        )
        templates.append(
            {
                "schema_version": "source_archive_result_v1",
                "archive_handoff_id": archive_handoff_id,
                "release_audit_id": release_audit_id,
                "release_index_id": release_index_id,
                "approved_release_id": approved_release_id,
                "queue_item_id": queue_item_id,
                "adapter_id": adapter,
                "source_url": source_url,
                "provider_id": provider_id,
                "provider_label": label,
                "result_status": "PENDING_OPERATOR_ENTRY",
                "archive_url": "",
                "archive_receipt_filename": "",
                "submitted_by": "",
                "observed_at_utc": "",
                "operator_notes": [],
            }
        )

    artifact_roles = sorted({artifact["role"] for artifact in artifacts})
    notes = _normalise_notes(handoff_notes, report.get("audit_notes") if isinstance(report.get("audit_notes"), list) else [])
    handoff_fingerprint = _stable_hash(
        {
            "archive_handoff_id": archive_handoff_id,
            "providers": providers,
            "source_url": source_url,
            "artifact_roles": artifact_roles,
            "audit_fingerprint": audit_fingerprint,
        },
        length=16,
    )

    archive_handoff_package = {
        "schema_version": SCHEMA_VERSION,
        "archive_handoff_id": archive_handoff_id,
        "handoff_status": "READY_FOR_MANUAL_ARCHIVE_SUBMISSION",
        "release_audit_id": release_audit_id,
        "release_index_id": release_index_id,
        "approved_release_id": approved_release_id,
        "evidence_review_package_id": evidence_review_package_id,
        "queue_item_id": queue_item_id,
        "total_export_package_id": total_export_package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "prepared_by": operator,
        "archive_provider_count": len(providers),
        "archive_providers": providers,
        "artifact_count": len(artifacts),
        "artifact_roles": artifact_roles,
        "artifact_index": artifacts,
        "audit_fingerprint": audit_fingerprint,
        "handoff_fingerprint": handoff_fingerprint,
        "manual_or_live_actions_started": False,
        "archive_submission_started": False,
        "live_network_default": False,
        "handoff_notes": notes,
    }

    provider_tasks = {
        "schema_version": PROVIDER_TASKS_SCHEMA_VERSION,
        "archive_handoff_id": archive_handoff_id,
        "release_audit_id": release_audit_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "task_status": "PENDING_OPERATOR_ACTION",
        "archive_submission_started": False,
        "manual_or_live_actions_started": False,
        "archive_tasks": archive_tasks,
    }

    result_templates = {
        "schema_version": RESULT_TEMPLATES_SCHEMA_VERSION,
        "archive_handoff_id": archive_handoff_id,
        "release_audit_id": release_audit_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "template_status": "WAITING_FOR_OPERATOR_RESULTS",
        "result_template_count": len(templates),
        "archive_result_templates": templates,
    }

    result_intake_handoff = {
        "schema_version": RESULT_INTAKE_HANDOFF_SCHEMA_VERSION,
        "archive_handoff_id": archive_handoff_id,
        "release_audit_id": release_audit_id,
        "release_index_id": release_index_id,
        "approved_release_id": approved_release_id,
        "queue_item_id": queue_item_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "handoff_status": "READY_FOR_ARCHIVE_RESULT_INTAKE",
        "required_next_stage": "source_archive_result_intake",
        "archive_provider_count": len(providers),
        "archive_providers": providers,
        "result_template_count": len(templates),
        "archive_submission_started": False,
        "manual_or_live_actions_started": False,
        "archive_result_inputs": [
            {
                "role": "source_archive_result_template",
                "provider_id": template["provider_id"],
                "filename_hint": f"{archive_handoff_id}.{template['provider_id']}.archive_result_template.json",
            }
            for template in templates
        ],
    }

    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "archive_handoff_id": archive_handoff_id,
        "release_audit_id": release_audit_id,
        "release_index_id": release_index_id,
        "approved_release_id": approved_release_id,
        "queue_item_id": queue_item_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "manual_or_live_actions_started": False,
        "archive_submission_started": False,
        "live_network_default": False,
        "input_mode": "explicit_release_audit_json_only",
        "handoff_status": "READY_FOR_MANUAL_ARCHIVE_SUBMISSION",
        "next_actions": [
            "Operator manually submits to selected archive providers only after explicit approval.",
            "Operator records archive URLs/receipts in the generated result templates.",
            "Pass completed result templates to the shared source_archive_result_intake stage.",
        ],
    }

    return SourceArchiveHandoffOutputs(
        archive_handoff_package=archive_handoff_package,
        provider_tasks=provider_tasks,
        result_templates=result_templates,
        result_intake_handoff=result_intake_handoff,
        operator_summary=operator_summary,
    )


def load_json_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def dump_json(data: Mapping[str, Any]) -> str:
    return _json_bytes(data).decode("utf-8")
