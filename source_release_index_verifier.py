from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA_VERSION = "source_release_index_verifier_v1"
_SAFE_NAME_RE = re.compile(r"^[^/\\:]+$")


def _is_safe_filename(value: object) -> bool:
    text = str(value or "")
    return bool(text) and bool(_SAFE_NAME_RE.match(text))


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def verify_source_release_index(
    release_index_record: Mapping[str, Any],
    release_inventory: Mapping[str, Any] | None = None,
    export_bundle_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    record = dict(release_index_record or {})
    inventory = dict(release_inventory or {})
    handoff = dict(export_bundle_handoff or {})

    if record.get("schema_version") != "source_release_index_v1":
        _issue(issues, "release index record schema_version must be source_release_index_v1")
    if record.get("release_index_status") != "READY_FOR_RELEASE_EXPORT_BUNDLE":
        _issue(issues, "release index record must be READY_FOR_RELEASE_EXPORT_BUNDLE")
    if not record.get("release_index_id"):
        _issue(issues, "release index record must include release_index_id")
    if not record.get("approved_release_id"):
        _issue(issues, "release index record must include approved_release_id")
    if not record.get("queue_item_id"):
        _issue(issues, "release index record must include queue_item_id")
    if not record.get("total_export_package_id"):
        _issue(issues, "release index record must include total_export_package_id")
    if not record.get("adapter_id"):
        _issue(issues, "release index record must include adapter_id")
    if not record.get("source_url"):
        _issue(issues, "release index record must include source_url")
    if not record.get("index_fingerprint"):
        _issue(issues, "release index record must include index_fingerprint")

    artifacts = record.get("artifact_index")
    if not isinstance(artifacts, list) or not artifacts:
        _issue(issues, "release index record must include non-empty artifact_index")
    else:
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, Mapping):
                _issue(issues, f"artifact_index[{index}] must be an object")
                continue
            if not _is_safe_filename(artifact.get("filename")):
                _issue(issues, f"artifact_index[{index}].filename must be a safe basename")
            if "path" in artifact or "absolute_path" in artifact:
                _issue(issues, f"artifact_index[{index}] must not include path or absolute_path")

    if inventory:
        if inventory.get("schema_version") != "source_release_inventory_v1":
            _issue(issues, "release inventory schema_version must be source_release_inventory_v1")
        if inventory.get("release_index_id") != record.get("release_index_id"):
            _issue(issues, "release inventory release_index_id mismatch")
        if inventory.get("inventory_status") != "READY_FOR_RELEASE_EXPORT_BUNDLE":
            _issue(issues, "release inventory must be READY_FOR_RELEASE_EXPORT_BUNDLE")
        entries = inventory.get("release_entries")
        if not isinstance(entries, list) or not entries:
            _issue(issues, "release inventory must include at least one release entry")

    if handoff:
        if handoff.get("schema_version") != "source_release_export_bundle_handoff_v1":
            _issue(issues, "export bundle handoff schema_version mismatch")
        if handoff.get("release_index_id") != record.get("release_index_id"):
            _issue(issues, "export bundle handoff release_index_id mismatch")
        if handoff.get("approved_release_id") != record.get("approved_release_id"):
            _issue(issues, "export bundle handoff approved_release_id mismatch")
        if handoff.get("handoff_status") != "READY_FOR_RELEASE_EXPORT_BUNDLE":
            _issue(issues, "export bundle handoff must be READY_FOR_RELEASE_EXPORT_BUNDLE")
        if handoff.get("required_next_stage") != "source_release_export_bundle":
            _issue(issues, "export bundle handoff required_next_stage must be source_release_export_bundle")

    if record.get("manual_or_live_actions_started") is True:
        _issue(issues, "release index stage must not mark manual_or_live_actions_started true")
    if record.get("live_network_default") is True:
        _issue(issues, "release index stage must not enable live_network_default")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "release_index_id": str(record.get("release_index_id") or ""),
        "approved_release_id": str(record.get("approved_release_id") or ""),
        "queue_item_id": str(record.get("queue_item_id") or ""),
        "adapter_id": str(record.get("adapter_id") or ""),
        "source_url": str(record.get("source_url") or ""),
    }
