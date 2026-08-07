from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA_VERSION = "source_pipeline_closeout_verifier_v1"
_EXPECTED_REPORT_SCHEMA = "source_pipeline_closeout_v1"
_EXPECTED_STAGE_COUNT = 15
_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+\.source_pipeline_closeout\.[0-9a-f]{12}$")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}


def _mapping(value: Any, *, name: str, issues: list[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        issues.append(f"{name} must be a JSON object")
        return {}
    return dict(value)


def _check_no_local_paths(value: Mapping[str, Any], *, name: str, issues: list[str]) -> None:
    present = sorted(_FORBIDDEN_PATH_FIELDS.intersection(value.keys()))
    if present:
        issues.append(f"{name} must not include local path fields: {', '.join(present)}")


def verify_source_pipeline_closeout(bundle: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    root = _mapping(bundle, name="bundle", issues=issues)
    report = _mapping(root.get("closeout_report"), name="closeout_report", issues=issues)
    inventory = _mapping(root.get("stage_inventory"), name="stage_inventory", issues=issues)
    handoff = _mapping(root.get("roadmap_closeout_handoff"), name="roadmap_closeout_handoff", issues=issues)
    summary = _mapping(root.get("operator_summary"), name="operator_summary", issues=issues)

    if report.get("schema_version") != _EXPECTED_REPORT_SCHEMA:
        issues.append("closeout_report.schema_version must be source_pipeline_closeout_v1")
    closeout_id = str(report.get("source_pipeline_closeout_id") or "")
    if not _ID_RE.match(closeout_id):
        issues.append("source_pipeline_closeout_id must use a safe deterministic id")
    source_url = str(report.get("source_url") or "")
    if not _URL_RE.match(source_url):
        issues.append("source_url must start with http:// or https://")
    if report.get("archive_decision") not in {"APPROVED", "REJECTED", "REVISION_REQUESTED"}:
        issues.append("archive_decision must be an allowed review decision")
    if report.get("final_status") not in {"SOURCE_PIPELINE_COMPLETE", "FOLLOW_UP_REQUIRED"}:
        issues.append("final_status must be SOURCE_PIPELINE_COMPLETE or FOLLOW_UP_REQUIRED")
    if bool(report.get("manual_or_live_actions_started")):
        issues.append("closeout must not start manual or live actions")
    if bool(report.get("live_network_default")):
        issues.append("closeout must not enable live network by default")

    stages = inventory.get("stages")
    if not isinstance(stages, list) or len(stages) != _EXPECTED_STAGE_COUNT:
        issues.append("stage_inventory.stages must contain all 15 shared pipeline stages")
    else:
        positions = [stage.get("position") for stage in stages if isinstance(stage, Mapping)]
        if positions != list(range(1, _EXPECTED_STAGE_COUNT + 1)):
            issues.append("stage_inventory stage positions must be contiguous from 1 to 15")
        if inventory.get("stage_count") != _EXPECTED_STAGE_COUNT:
            issues.append("stage_inventory.stage_count must be 15")
        if report.get("final_status") == "SOURCE_PIPELINE_COMPLETE":
            incomplete = [stage.get("stage_id") for stage in stages if isinstance(stage, Mapping) and stage.get("status") != "COMPLETE"]
            if incomplete:
                issues.append("SOURCE_PIPELINE_COMPLETE requires every shared stage to be COMPLETE")

    if handoff.get("source_pipeline_closeout_id") != closeout_id:
        issues.append("roadmap handoff must reference the closeout id")
    if summary.get("source_pipeline_closeout_id") != closeout_id:
        issues.append("operator summary must reference the closeout id")
    if bool(handoff.get("manual_or_live_actions_started")) or bool(summary.get("manual_or_live_actions_started")):
        issues.append("handoff/summary must not start manual or live actions")

    for name, mapping in (("closeout_report", report), ("roadmap_closeout_handoff", handoff), ("operator_summary", summary)):
        _check_no_local_paths(mapping, name=name, issues=issues)

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_pipeline_closeout_id": closeout_id,
        "adapter_id": report.get("adapter_id"),
        "source_url": report.get("source_url"),
        "final_status": report.get("final_status"),
        "archive_decision": report.get("archive_decision"),
    }
