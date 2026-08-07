from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA_VERSION = "source_archive_handoff_verifier_v1"
_SAFE_NAME_RE = re.compile(r"^[^/\\:]+$")


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def _is_safe_filename(value: object) -> bool:
    text = str(value or "")
    return bool(text) and bool(_SAFE_NAME_RE.match(text))


def verify_source_archive_handoff(
    archive_handoff_package: Mapping[str, Any],
    provider_tasks: Mapping[str, Any] | None = None,
    result_templates: Mapping[str, Any] | None = None,
    result_intake_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    package = dict(archive_handoff_package or {})
    tasks_doc = dict(provider_tasks or {})
    templates_doc = dict(result_templates or {})
    intake = dict(result_intake_handoff or {})

    if package.get("schema_version") != "source_archive_handoff_v1":
        _issue(issues, "archive handoff package schema_version must be source_archive_handoff_v1")
    if package.get("handoff_status") != "READY_FOR_MANUAL_ARCHIVE_SUBMISSION":
        _issue(issues, "archive handoff package must be READY_FOR_MANUAL_ARCHIVE_SUBMISSION")
    for key in ("archive_handoff_id", "release_audit_id", "release_index_id", "approved_release_id", "queue_item_id", "adapter_id", "source_url"):
        if not package.get(key):
            _issue(issues, f"archive handoff package must include {key}")
    if package.get("archive_submission_started") is True:
        _issue(issues, "archive handoff must not mark archive_submission_started true")
    if package.get("manual_or_live_actions_started") is True:
        _issue(issues, "archive handoff must not mark manual_or_live_actions_started true")
    if package.get("live_network_default") is True:
        _issue(issues, "archive handoff must not enable live_network_default")

    artifacts = package.get("artifact_index")
    if not isinstance(artifacts, list) or not artifacts:
        _issue(issues, "archive handoff package must include non-empty artifact_index")
    else:
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, Mapping):
                _issue(issues, f"artifact_index[{index}] must be an object")
                continue
            if not _is_safe_filename(artifact.get("filename")):
                _issue(issues, f"artifact_index[{index}].filename must be a safe basename")
            if "path" in artifact or "absolute_path" in artifact:
                _issue(issues, f"artifact_index[{index}] must not include path or absolute_path")

    providers = package.get("archive_providers")
    if not isinstance(providers, list) or not providers:
        _issue(issues, "archive handoff package must include archive providers")

    if tasks_doc:
        if tasks_doc.get("schema_version") != "source_archive_provider_tasks_v1":
            _issue(issues, "provider tasks schema_version mismatch")
        if tasks_doc.get("archive_handoff_id") != package.get("archive_handoff_id"):
            _issue(issues, "provider tasks archive_handoff_id mismatch")
        if tasks_doc.get("archive_submission_started") is True:
            _issue(issues, "provider tasks must not mark archive submission started")
        tasks = tasks_doc.get("archive_tasks")
        if not isinstance(tasks, list) or not tasks:
            _issue(issues, "provider tasks must include archive_tasks")
        else:
            for index, task in enumerate(tasks):
                if not isinstance(task, Mapping):
                    _issue(issues, f"archive_tasks[{index}] must be an object")
                    continue
                if task.get("task_status") != "PENDING_OPERATOR_ACTION":
                    _issue(issues, f"archive_tasks[{index}] must be PENDING_OPERATOR_ACTION")
                if task.get("approval_required_before_submission") is not True:
                    _issue(issues, f"archive_tasks[{index}] must require approval before submission")
                if task.get("archive_submission_started") is True:
                    _issue(issues, f"archive_tasks[{index}] must not mark archive submission started")
                if not _is_safe_filename(task.get("result_template_filename")):
                    _issue(issues, f"archive_tasks[{index}].result_template_filename must be a safe basename")

    if templates_doc:
        if templates_doc.get("schema_version") != "source_archive_result_templates_v1":
            _issue(issues, "result templates schema_version mismatch")
        if templates_doc.get("archive_handoff_id") != package.get("archive_handoff_id"):
            _issue(issues, "result templates archive_handoff_id mismatch")
        templates = templates_doc.get("archive_result_templates")
        if not isinstance(templates, list) or not templates:
            _issue(issues, "result templates must include archive_result_templates")
        else:
            for index, template in enumerate(templates):
                if not isinstance(template, Mapping):
                    _issue(issues, f"archive_result_templates[{index}] must be an object")
                    continue
                if template.get("result_status") != "PENDING_OPERATOR_ENTRY":
                    _issue(issues, f"archive_result_templates[{index}] must be PENDING_OPERATOR_ENTRY")
                if template.get("archive_url"):
                    _issue(issues, f"archive_result_templates[{index}].archive_url must be blank before result intake")
                if template.get("archive_receipt_filename") and not _is_safe_filename(template.get("archive_receipt_filename")):
                    _issue(issues, f"archive_result_templates[{index}].archive_receipt_filename must be a safe basename")

    if intake:
        if intake.get("schema_version") != "source_archive_result_intake_handoff_v1":
            _issue(issues, "result intake handoff schema_version mismatch")
        if intake.get("archive_handoff_id") != package.get("archive_handoff_id"):
            _issue(issues, "result intake handoff archive_handoff_id mismatch")
        if intake.get("handoff_status") != "READY_FOR_ARCHIVE_RESULT_INTAKE":
            _issue(issues, "result intake handoff must be READY_FOR_ARCHIVE_RESULT_INTAKE")
        if intake.get("required_next_stage") != "source_archive_result_intake":
            _issue(issues, "result intake handoff required_next_stage must be source_archive_result_intake")
        if intake.get("archive_submission_started") is True:
            _issue(issues, "result intake handoff must not mark archive submission started")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "archive_handoff_id": str(package.get("archive_handoff_id") or ""),
        "release_audit_id": str(package.get("release_audit_id") or ""),
        "release_index_id": str(package.get("release_index_id") or ""),
        "approved_release_id": str(package.get("approved_release_id") or ""),
        "queue_item_id": str(package.get("queue_item_id") or ""),
        "adapter_id": str(package.get("adapter_id") or ""),
        "source_url": str(package.get("source_url") or ""),
    }
