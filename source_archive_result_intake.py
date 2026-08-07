from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "source_archive_result_intake_v1"
RECEIPT_INDEX_SCHEMA_VERSION = "source_archive_receipt_index_v1"
ARCHIVE_REVIEW_HANDOFF_SCHEMA_VERSION = "source_archive_review_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_archive_result_intake_operator_summary_v1"
OPERATOR_RESULT_SCHEMA_VERSION = "source_archive_operator_result_v1"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_SAFE_NAME_RE = re.compile(r"^[^/\\:]+$")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


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


def _safe_basename(value: object, *, required: bool = False) -> str:
    text = str(value or "").strip()
    if not text:
        if required:
            raise ValueError("safe filename is required")
        return ""
    if not _SAFE_NAME_RE.match(text):
        raise ValueError("archive result intake filenames must be safe basenames, not paths")
    return text


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


def _normalise_task_providers(provider_tasks: Mapping[str, Any] | None) -> list[str]:
    tasks_doc = _coerce_mapping(provider_tasks, name="provider_tasks") if provider_tasks else {}
    if not tasks_doc:
        return []
    if tasks_doc.get("schema_version") != "source_archive_provider_tasks_v1":
        raise ValueError("provider_tasks schema_version must be source_archive_provider_tasks_v1")
    tasks = tasks_doc.get("archive_tasks")
    if not isinstance(tasks, list):
        raise ValueError("provider_tasks.archive_tasks must be a list")
    providers: list[str] = []
    for task in tasks:
        if not isinstance(task, Mapping):
            continue
        providers.append(_clean_identifier(task.get("provider_id"), fallback="archive_provider"))
    return sorted(set(providers))


def _normalise_template_providers(result_templates: Mapping[str, Any] | None) -> list[str]:
    templates_doc = _coerce_mapping(result_templates, name="result_templates") if result_templates else {}
    if not templates_doc:
        return []
    if templates_doc.get("schema_version") != "source_archive_result_templates_v1":
        raise ValueError("result_templates schema_version must be source_archive_result_templates_v1")
    templates = templates_doc.get("archive_result_templates")
    if not isinstance(templates, list):
        raise ValueError("result_templates.archive_result_templates must be a list")
    providers: list[str] = []
    for template in templates:
        if not isinstance(template, Mapping):
            continue
        providers.append(_clean_identifier(template.get("provider_id"), fallback="archive_provider"))
    return sorted(set(providers))


def _normalise_operator_results(operator_archive_results: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not operator_archive_results:
        raise ValueError("at least one operator archive result is required")

    normalised: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, raw_result in enumerate(operator_archive_results):
        if not isinstance(raw_result, Mapping):
            raise TypeError(f"operator_archive_results[{index}] must be a JSON object")
        result = dict(raw_result)
        schema = str(result.get("schema_version") or OPERATOR_RESULT_SCHEMA_VERSION)
        if schema != OPERATOR_RESULT_SCHEMA_VERSION:
            raise ValueError(f"operator_archive_results[{index}] schema_version must be {OPERATOR_RESULT_SCHEMA_VERSION}")
        provider_id = _clean_identifier(result.get("provider_id"), fallback="archive_provider")
        archive_url = str(result.get("archive_url") or result.get("url") or "").strip()
        if not archive_url:
            raise ValueError(f"operator_archive_results[{index}].archive_url is required")
        if not _URL_RE.match(archive_url):
            raise ValueError(f"operator_archive_results[{index}].archive_url must start with http:// or https://")
        receipt_filename = _safe_basename(
            result.get("archive_receipt_filename") or result.get("receipt_filename") or result.get("filename")
        )
        screenshot_filename = _safe_basename(result.get("archive_screenshot_filename") or result.get("screenshot_filename"))
        if "path" in result or "absolute_path" in result or "local_path" in result:
            raise ValueError(f"operator_archive_results[{index}] must not include local path fields")
        key = (provider_id, archive_url)
        if key in seen:
            continue
        seen.add(key)
        normalised.append(
            {
                "schema_version": OPERATOR_RESULT_SCHEMA_VERSION,
                "provider_id": provider_id,
                "result_status": "OPERATOR_SUPPLIED_PENDING_REVIEW",
                "archive_url": archive_url,
                "archive_receipt_filename": receipt_filename,
                "archive_screenshot_filename": screenshot_filename,
                "operator_result_supplied": True,
                "online_validation_performed": False,
                "archive_submission_performed_by_app": False,
                "manual_or_live_actions_started_by_app": False,
                "operator_notes": _normalise_notes(result.get("operator_notes") if isinstance(result.get("operator_notes"), list) else None),
            }
        )
    if not normalised:
        raise ValueError("at least one unique operator archive result is required")
    normalised.sort(key=lambda entry: (entry["provider_id"], entry["archive_url"]))
    return normalised


@dataclass(frozen=True)
class SourceArchiveResultIntakeOutputs:
    archive_result_intake_record: dict[str, Any]
    archive_receipt_index: dict[str, Any]
    archive_review_handoff: dict[str, Any]
    operator_summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "archive_result_intake_record": self.archive_result_intake_record,
            "archive_receipt_index": self.archive_receipt_index,
            "archive_review_handoff": self.archive_review_handoff,
            "operator_summary": self.operator_summary,
        }


def build_source_archive_result_intake(
    *,
    archive_handoff_package: Mapping[str, Any],
    operator_archive_results: Sequence[Mapping[str, Any]],
    provider_tasks: Mapping[str, Any] | None = None,
    result_templates: Mapping[str, Any] | None = None,
    result_intake_handoff: Mapping[str, Any] | None = None,
    operator_id: str = "manual_archive_operator",
    intake_notes: Iterable[str] | None = None,
) -> SourceArchiveResultIntakeOutputs:
    package = _coerce_mapping(archive_handoff_package, name="archive_handoff_package")
    tasks_doc = _coerce_mapping(provider_tasks, name="provider_tasks") if provider_tasks else {}
    templates_doc = _coerce_mapping(result_templates, name="result_templates") if result_templates else {}
    intake_handoff = _coerce_mapping(result_intake_handoff, name="result_intake_handoff") if result_intake_handoff else {}

    if package.get("schema_version") != "source_archive_handoff_v1":
        raise ValueError("archive_handoff_package schema_version must be source_archive_handoff_v1")
    if package.get("handoff_status") != "READY_FOR_MANUAL_ARCHIVE_SUBMISSION":
        raise ValueError("archive_handoff_package.handoff_status must be READY_FOR_MANUAL_ARCHIVE_SUBMISSION")
    if package.get("archive_submission_started") is True:
        raise ValueError("archive_handoff_package must not mark archive_submission_started true")
    if package.get("manual_or_live_actions_started") is True:
        raise ValueError("archive_handoff_package must not mark manual_or_live_actions_started true")

    archive_handoff_id = _clean_identifier(package.get("archive_handoff_id"), fallback="source.archive_handoff")
    release_audit_id = _clean_identifier(package.get("release_audit_id"), fallback="source.release_audit")
    release_index_id = _clean_identifier(package.get("release_index_id"), fallback="source.release_index")
    approved_release_id = _clean_identifier(package.get("approved_release_id"), fallback="source.approved_release")
    evidence_review_package_id = _clean_identifier(package.get("evidence_review_package_id"), fallback="source.evidence_review")
    queue_item_id = _clean_identifier(package.get("queue_item_id"), fallback="source.evidence_queue")
    total_export_package_id = _clean_identifier(package.get("total_export_package_id"), fallback="source.total_export_package")
    capture_bundle_id = _clean_identifier(package.get("capture_bundle_id"), fallback="source.capture_bundle")
    adapter = _clean_identifier(package.get("adapter_id"), fallback="source")
    source_url = str(package.get("source_url") or "").strip()
    if not source_url:
        raise ValueError("archive_handoff_package.source_url is required")

    package_providers = sorted({_clean_identifier(provider, fallback="archive_provider") for provider in package.get("archive_providers", [])})
    if not package_providers:
        raise ValueError("archive_handoff_package.archive_providers is required")

    if tasks_doc:
        if tasks_doc.get("archive_handoff_id") != archive_handoff_id:
            raise ValueError("provider_tasks.archive_handoff_id mismatch")
        task_providers = _normalise_task_providers(tasks_doc)
        if task_providers and not set(task_providers).issubset(set(package_providers)):
            raise ValueError("provider_tasks include provider ids outside archive_handoff_package.archive_providers")
    if templates_doc:
        if templates_doc.get("archive_handoff_id") != archive_handoff_id:
            raise ValueError("result_templates.archive_handoff_id mismatch")
        template_providers = _normalise_template_providers(templates_doc)
        if template_providers and not set(template_providers).issubset(set(package_providers)):
            raise ValueError("result_templates include provider ids outside archive_handoff_package.archive_providers")
    if intake_handoff:
        if intake_handoff.get("schema_version") != "source_archive_result_intake_handoff_v1":
            raise ValueError("result_intake_handoff schema_version mismatch")
        if intake_handoff.get("archive_handoff_id") != archive_handoff_id:
            raise ValueError("result_intake_handoff.archive_handoff_id mismatch")
        if intake_handoff.get("handoff_status") != "READY_FOR_ARCHIVE_RESULT_INTAKE":
            raise ValueError("result_intake_handoff must be READY_FOR_ARCHIVE_RESULT_INTAKE")

    results = _normalise_operator_results(operator_archive_results)
    result_providers = {result["provider_id"] for result in results}
    unknown_providers = sorted(result_providers.difference(package_providers))
    if unknown_providers:
        raise ValueError("operator archive results include provider ids not present in archive_handoff_package.archive_providers: " + ", ".join(unknown_providers))

    operator = _clean_identifier(operator_id, fallback="manual_archive_operator")
    intake_seed = {
        "archive_handoff_id": archive_handoff_id,
        "release_audit_id": release_audit_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "operator_results": results,
    }
    archive_result_intake_id = f"{adapter}.archive_result_intake.{_stable_hash(intake_seed)}"

    receipt_entries: list[dict[str, Any]] = []
    for result in results:
        receipt_seed = {
            "archive_result_intake_id": archive_result_intake_id,
            "provider_id": result["provider_id"],
            "archive_url": result["archive_url"],
        }
        receipt_entries.append(
            {
                "archive_receipt_id": f"{archive_result_intake_id}.{result['provider_id']}.{_stable_hash(receipt_seed, length=8)}",
                "provider_id": result["provider_id"],
                "archive_url": result["archive_url"],
                "archive_receipt_filename": result["archive_receipt_filename"],
                "archive_screenshot_filename": result["archive_screenshot_filename"],
                "receipt_status": "RECEIVED_PENDING_ARCHIVE_REVIEW",
                "operator_result_supplied": True,
                "online_validation_performed": False,
                "archive_submission_performed_by_app": False,
            }
        )

    received_provider_ids = sorted(result_providers)
    missing_provider_ids = [provider_id for provider_id in package_providers if provider_id not in result_providers]
    intake_status = "READY_FOR_ARCHIVE_REVIEW" if receipt_entries else "PENDING_OPERATOR_RESULTS"

    archive_result_intake_record = {
        "schema_version": SCHEMA_VERSION,
        "archive_result_intake_id": archive_result_intake_id,
        "archive_handoff_id": archive_handoff_id,
        "release_audit_id": release_audit_id,
        "release_index_id": release_index_id,
        "approved_release_id": approved_release_id,
        "evidence_review_package_id": evidence_review_package_id,
        "queue_item_id": queue_item_id,
        "total_export_package_id": total_export_package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "intake_status": intake_status,
        "archive_providers": package_providers,
        "received_provider_ids": received_provider_ids,
        "missing_provider_ids": missing_provider_ids,
        "operator_archive_results": results,
        "operator_id": operator,
        "operator_supplied_result_count": len(results),
        "operator_supplied_results_received": True,
        "online_validation_performed": False,
        "archive_submission_performed_by_app": False,
        "manual_or_live_actions_started_by_app": False,
        "required_next_stage": "source_archive_review",
        "intake_notes": _normalise_notes(intake_notes),
    }

    archive_receipt_index = {
        "schema_version": RECEIPT_INDEX_SCHEMA_VERSION,
        "archive_result_intake_id": archive_result_intake_id,
        "archive_handoff_id": archive_handoff_id,
        "release_audit_id": release_audit_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "receipt_count": len(receipt_entries),
        "receipt_status": "RECEIVED_PENDING_ARCHIVE_REVIEW",
        "receipt_entries": receipt_entries,
        "online_validation_performed": False,
        "archive_submission_performed_by_app": False,
    }

    archive_review_handoff = {
        "schema_version": ARCHIVE_REVIEW_HANDOFF_SCHEMA_VERSION,
        "handoff_status": "READY_FOR_ARCHIVE_REVIEW",
        "archive_result_intake_id": archive_result_intake_id,
        "archive_handoff_id": archive_handoff_id,
        "release_audit_id": release_audit_id,
        "release_index_id": release_index_id,
        "approved_release_id": approved_release_id,
        "queue_item_id": queue_item_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "receipt_count": len(receipt_entries),
        "received_provider_ids": received_provider_ids,
        "missing_provider_ids": missing_provider_ids,
        "required_next_stage": "source_archive_review",
        "online_validation_performed": False,
        "archive_submission_performed_by_app": False,
    }

    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "archive_result_intake_id": archive_result_intake_id,
        "archive_handoff_id": archive_handoff_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "status": intake_status,
        "operator_supplied_result_count": len(results),
        "received_provider_ids": received_provider_ids,
        "missing_provider_ids": missing_provider_ids,
        "manual_or_live_actions_started_by_app": False,
        "online_validation_performed": False,
        "archive_submission_performed_by_app": False,
        "next_actions": [
            "Review each operator-supplied archive URL/receipt in the shared Archive Review stage.",
            "Do not treat archive URLs as verified until Archive Review records an explicit decision.",
            "Keep provider-specific behavior as data and fixtures unless a provider needs genuinely unique handling.",
        ],
    }

    return SourceArchiveResultIntakeOutputs(
        archive_result_intake_record=archive_result_intake_record,
        archive_receipt_index=archive_receipt_index,
        archive_review_handoff=archive_review_handoff,
        operator_summary=operator_summary,
    )


def dump_json(data: Mapping[str, Any]) -> str:
    return _json_bytes(data).decode("utf-8")


def load_json_file(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
