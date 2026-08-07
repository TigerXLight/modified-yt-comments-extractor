from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "source_adapter_capture_action_kit_v1"
ACTION_INDEX_SCHEMA_VERSION = "source_adapter_capture_action_index_v1"
ARTIFACT_TEMPLATE_SCHEMA_VERSION = "source_adapter_capture_artifact_intake_templates_v1"
SESSION_HANDOFF_SCHEMA_VERSION = "source_adapter_capture_session_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_capture_action_operator_summary_v1"
ACTION_KIT_STATUS = "READY_FOR_OPERATOR_APPROVED_CAPTURE_ACTIONS"
SESSION_HANDOFF_STATUS = "READY_FOR_OPERATOR_APPROVED_CAPTURE_SESSION"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_SAFE_BASENAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

DEFAULT_ARTIFACT_ROLES = [
    "article_html_or_text",
    "metadata_json",
    "screenshot",
]

FORBIDDEN_RUNTIME_EFFECTS = [
    "fetch_url",
    "launch_browser",
    "scan_folder",
    "read_credentials",
    "submit_archive",
    "upload_release",
    "mutate_app_files",
    "mutate_registry_files",
    "start_live_action",
]


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _stable_hash(value: Any, *, length: int = 12) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()[:length]


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return value


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _safe_id(value: Any, *, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} is required")
    if not _SAFE_ID_RE.match(text):
        raise ValueError(f"{label} must be a safe identifier: {text!r}")
    if ".." in text or text.startswith((".", "-")):
        raise ValueError(f"{label} must not contain traversal-like segments: {text!r}")
    return text


def _safe_basename(value: str, *, label: str) -> str:
    text = str(value or "").strip()
    if not text or not _SAFE_BASENAME_RE.match(text) or ".." in text or text.startswith((".", "-")):
        raise ValueError(f"{label} must be a safe basename: {text!r}")
    return text


def _safe_text(value: Any, default: str = "") -> str:
    text = str(value or default).strip()
    return text if text else default


def _unique_strings(values: Sequence[Any]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _find_adapter_list(mapping: Mapping[str, Any]) -> list[Any]:
    for key in (
        "adapters",
        "selected_adapters",
        "source_options",
        "adapter_options",
        "capture_routes",
        "adapter_capture_setups",
    ):
        value = mapping.get(key)
        if isinstance(value, list) and value:
            return value

    for key in (
        "capture_setup_plan",
        "source_selection_package",
        "source_adapter_source_selection_package",
        "source_adapter_capture_setup_package",
        "source_adapter_registry_rollout_package",
    ):
        nested = mapping.get(key)
        if isinstance(nested, Mapping):
            nested_list = _find_adapter_list(nested)
            if nested_list:
                return nested_list

    index = mapping.get("capture_route_index") or mapping.get("adapter_option_index")
    if isinstance(index, Mapping):
        for key in ("routes", "options", "adapters"):
            value = index.get(key)
            if isinstance(value, list) and value:
                return value

    return []


def _artifact_roles_from(source: Mapping[str, Any]) -> list[str]:
    candidates: list[Any] = []
    for key in ("artifact_roles", "required_artifact_roles", "expected_artifact_roles"):
        candidates.extend(_as_list(source.get(key)))
    artifact_intake = source.get("artifact_intake") or source.get("artifact_intake_plan")
    if isinstance(artifact_intake, Mapping):
        candidates.extend(_as_list(artifact_intake.get("artifact_roles")))
    roles = [_safe_id(role, label="artifact role") for role in _unique_strings(candidates)]
    return roles or list(DEFAULT_ARTIFACT_ROLES)


def _normalise_adapter(adapter: Mapping[str, Any], ordinal: int) -> dict[str, Any]:
    adapter_id = _safe_id(
        adapter.get("adapter_id") or adapter.get("id") or adapter.get("source_adapter_id") or f"adapter_{ordinal}",
        label="adapter_id",
    )
    artifact_roles = _artifact_roles_from(adapter)
    source_kind = _safe_text(adapter.get("source_kind"), "web")
    display_name = _safe_text(adapter.get("display_name") or adapter.get("label"), adapter_id.replace("_", " ").title())
    route_id = _safe_id(adapter.get("capture_route_id") or f"{adapter_id}.capture_route", label="capture_route_id")
    return {
        "adapter_id": adapter_id,
        "display_name": display_name,
        "source_kind": source_kind,
        "capture_route_id": route_id,
        "artifact_roles": artifact_roles,
        "operator_only": bool(adapter.get("operator_only", True)),
        "requires_lightweight_browser": bool(adapter.get("requires_lightweight_browser", True)),
        "live_network_default": bool(adapter.get("live_network_default", False)),
    }


def _normalise_adapters(capture_setup_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_adapters = _find_adapter_list(capture_setup_package)
    if not raw_adapters:
        raise ValueError("capture setup package must contain at least one adapter/source option")

    adapters: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ordinal, raw_adapter in enumerate(raw_adapters, start=1):
        adapter = _as_mapping(raw_adapter, "adapter")
        normalised = _normalise_adapter(adapter, ordinal)
        adapter_id = normalised["adapter_id"]
        if adapter_id in seen:
            raise ValueError(f"duplicate adapter_id: {adapter_id}")
        seen.add(adapter_id)
        adapters.append(normalised)
    return adapters


def _template_filename(adapter_id: str, role: str) -> str:
    return _safe_basename(f"{adapter_id}.{role}.artifact_receipt.json", label="artifact template filename")


def _build_actions(adapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for adapter in adapters:
        adapter_id = adapter["adapter_id"]
        actions.append(
            {
                "action_id": f"{adapter_id}.operator_capture_preflight",
                "adapter_id": adapter_id,
                "action_type": "operator_capture_preflight",
                "status": "READY_FOR_OPERATOR_APPROVAL",
                "requires_explicit_approval": True,
                "requires_execute_approved_flag": True,
                "starts_live_or_manual_action": False,
                "runtime_effects": [],
                "checklist": [
                    "Confirm the selected adapter/source option.",
                    "Confirm the operator-supplied source URL outside this package.",
                    "Confirm the output folder and artifact role list before capture.",
                ],
            }
        )
        actions.append(
            {
                "action_id": f"{adapter_id}.artifact_intake_preparation",
                "adapter_id": adapter_id,
                "action_type": "artifact_intake_preparation",
                "status": "READY_FOR_OPERATOR_APPROVAL",
                "requires_explicit_approval": True,
                "requires_execute_approved_flag": True,
                "starts_live_or_manual_action": False,
                "runtime_effects": [],
                "artifact_roles": list(adapter["artifact_roles"]),
            }
        )
    return actions


def _build_artifact_templates(adapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    templates: list[dict[str, Any]] = []
    for adapter in adapters:
        adapter_id = adapter["adapter_id"]
        for role in adapter["artifact_roles"]:
            templates.append(
                {
                    "adapter_id": adapter_id,
                    "artifact_role": role,
                    "template_filename": _template_filename(adapter_id, role),
                    "schema_version": "source_adapter_capture_artifact_receipt_template_v1",
                    "required_fields": [
                        "adapter_id",
                        "artifact_role",
                        "artifact_basename",
                        "byte_count",
                        "sha256",
                    ],
                    "placeholder_values": {
                        "adapter_id": adapter_id,
                        "artifact_role": role,
                        "artifact_basename": "REPLACE_WITH_SAFE_BASENAME",
                        "byte_count": "REPLACE_WITH_NON_NEGATIVE_INTEGER",
                        "sha256": "REPLACE_WITH_64_HEX_SHA256",
                    },
                }
            )
    return templates


def build_source_adapter_capture_action_kit(
    capture_setup_package: Mapping[str, Any],
    *,
    operator_profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic local-only action kit from an Adapter Capture Setup package."""

    source_package = _as_mapping(capture_setup_package, "capture_setup_package")
    profile = deepcopy(dict(operator_profile or {}))
    adapters = _normalise_adapters(source_package)
    source_adapter_capture_setup_id = _safe_text(
        source_package.get("source_adapter_capture_setup_id")
        or source_package.get("capture_setup_id")
        or source_package.get("source_adapter_source_selection_id"),
        "",
    )

    action_index = {
        "schema_version": ACTION_INDEX_SCHEMA_VERSION,
        "action_kit_status": ACTION_KIT_STATUS,
        "adapter_count": len(adapters),
        "action_count": len(adapters) * 2,
        "actions": _build_actions(adapters),
    }
    artifact_templates = {
        "schema_version": ARTIFACT_TEMPLATE_SCHEMA_VERSION,
        "adapter_count": len(adapters),
        "template_count": sum(len(adapter["artifact_roles"]) for adapter in adapters),
        "templates": _build_artifact_templates(adapters),
    }
    capture_session_handoff = {
        "schema_version": SESSION_HANDOFF_SCHEMA_VERSION,
        "status": SESSION_HANDOFF_STATUS,
        "source_adapter_capture_setup_id": source_adapter_capture_setup_id,
        "requires_operator_approval_before_execution": True,
        "requires_explicit_source_url": True,
        "requires_explicit_output_directory": True,
        "manual_or_live_actions_started": False,
        "artifact_receipt_templates_ready": True,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": ACTION_KIT_STATUS,
        "adapter_count": len(adapters),
        "live_network_default": False,
        "manual_or_live_actions_started": False,
        "next_actions": [
            "Use the generated action index to present capture actions to the operator.",
            "Require explicit operator approval before loading any URL or writing capture artifacts.",
            "Fill artifact receipt templates only after operator-approved capture creates local artifacts.",
        ],
    }

    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "source_adapter_capture_setup_id": source_adapter_capture_setup_id,
        "action_kit_status": ACTION_KIT_STATUS,
        "adapters": adapters,
        "adapter_count": len(adapters),
        "action_index": action_index,
        "artifact_intake_templates": artifact_templates,
        "capture_session_handoff": capture_session_handoff,
        "operator_summary": operator_summary,
        "operator_profile": profile,
        "safety_contract": {
            "live_network_default": False,
            "manual_or_live_actions_started": False,
            "requires_explicit_approval": True,
            "requires_execute_approved_flag": True,
            "forbidden_runtime_effects": list(FORBIDDEN_RUNTIME_EFFECTS),
        },
    }
    action_kit_id = f"source_adapter_capture_action_kit.{_stable_hash(unsigned)}"
    package = dict(unsigned)
    package["source_adapter_capture_action_kit_id"] = action_kit_id
    package["action_index"] = dict(action_index, source_adapter_capture_action_kit_id=action_kit_id)
    package["artifact_intake_templates"] = dict(
        artifact_templates,
        source_adapter_capture_action_kit_id=action_kit_id,
    )
    package["capture_session_handoff"] = dict(
        capture_session_handoff,
        source_adapter_capture_action_kit_id=action_kit_id,
    )
    package["operator_summary"] = dict(
        operator_summary,
        source_adapter_capture_action_kit_id=action_kit_id,
    )
    return package


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_capture_action_kit_package": dict(pkg),
        "source_adapter_capture_action_index": deepcopy(pkg.get("action_index", {})),
        "source_adapter_capture_artifact_intake_templates": deepcopy(pkg.get("artifact_intake_templates", {})),
        "source_adapter_capture_session_handoff": deepcopy(pkg.get("capture_session_handoff", {})),
        "source_adapter_capture_action_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    sample = {
        "source_adapter_capture_setup_id": "source_adapter_capture_setup.example",
        "adapters": [
            {
                "adapter_id": "article",
                "display_name": "Article",
                "source_kind": "web",
                "artifact_roles": ["article_html_or_text", "metadata_json", "screenshot"],
            }
        ],
    }
    built = build_source_adapter_capture_action_kit(sample)
    assert built["action_kit_status"] == ACTION_KIT_STATUS
    assert built["adapter_count"] == 1
    assert built["capture_session_handoff"]["manual_or_live_actions_started"] is False
    print("Source Adapter Capture Action Kit self-test passed.")
