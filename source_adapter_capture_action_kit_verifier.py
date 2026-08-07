from __future__ import annotations

import re
from typing import Any, Mapping

from source_adapter_capture_action_kit import ACTION_KIT_STATUS, SCHEMA_VERSION

_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_SHA_PLACEHOLDER = "REPLACE_WITH_64_HEX_SHA256"


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ID_RE.match(value)) and ".." not in value


def verify_source_adapter_capture_action_kit(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        _issue(issues, "schema_version is not source_adapter_capture_action_kit_v1")
    action_kit_id = package.get("source_adapter_capture_action_kit_id")
    if not _valid_id(action_kit_id):
        _issue(issues, "source_adapter_capture_action_kit_id is missing or unsafe")
    if package.get("action_kit_status") != ACTION_KIT_STATUS:
        _issue(issues, "action_kit_status is not READY_FOR_OPERATOR_APPROVED_CAPTURE_ACTIONS")

    adapters = package.get("adapters")
    if not isinstance(adapters, list) or not adapters:
        _issue(issues, "adapters must be a non-empty list")
    else:
        seen: set[str] = set()
        for adapter in adapters:
            if not isinstance(adapter, Mapping):
                _issue(issues, "adapter row is not a mapping")
                continue
            adapter_id = adapter.get("adapter_id")
            if not _valid_id(adapter_id):
                _issue(issues, f"adapter_id is missing or unsafe: {adapter_id!r}")
            elif adapter_id in seen:
                _issue(issues, f"duplicate adapter_id: {adapter_id}")
            else:
                seen.add(adapter_id)
            roles = adapter.get("artifact_roles")
            if not isinstance(roles, list) or not roles:
                _issue(issues, f"adapter {adapter_id!r} has no artifact roles")

    safety = package.get("safety_contract")
    if not isinstance(safety, Mapping):
        _issue(issues, "safety_contract is missing")
    else:
        if safety.get("live_network_default") is not False:
            _issue(issues, "live_network_default must be false")
        if safety.get("manual_or_live_actions_started") is not False:
            _issue(issues, "manual_or_live_actions_started must be false")
        if safety.get("requires_explicit_approval") is not True:
            _issue(issues, "requires_explicit_approval must be true")
        if safety.get("requires_execute_approved_flag") is not True:
            _issue(issues, "requires_execute_approved_flag must be true")

    action_index = package.get("action_index")
    if not isinstance(action_index, Mapping):
        _issue(issues, "action_index is missing")
    else:
        actions = action_index.get("actions")
        if not isinstance(actions, list) or not actions:
            _issue(issues, "action_index.actions must be non-empty")
        else:
            for action in actions:
                if not isinstance(action, Mapping):
                    _issue(issues, "action is not a mapping")
                    continue
                if action.get("requires_explicit_approval") is not True:
                    _issue(issues, f"action {action.get('action_id')!r} does not require explicit approval")
                if action.get("requires_execute_approved_flag") is not True:
                    _issue(issues, f"action {action.get('action_id')!r} does not require execute-approved flag")
                if action.get("starts_live_or_manual_action") is not False:
                    _issue(issues, f"action {action.get('action_id')!r} starts live/manual actions")
                if action.get("runtime_effects") not in ([], None):
                    _issue(issues, f"action {action.get('action_id')!r} declares runtime effects")

    handoff = package.get("capture_session_handoff")
    if not isinstance(handoff, Mapping):
        _issue(issues, "capture_session_handoff is missing")
    else:
        if handoff.get("manual_or_live_actions_started") is not False:
            _issue(issues, "handoff must not start manual/live actions")
        if handoff.get("requires_operator_approval_before_execution") is not True:
            _issue(issues, "handoff must require operator approval")

    templates = package.get("artifact_intake_templates")
    if not isinstance(templates, Mapping):
        _issue(issues, "artifact_intake_templates is missing")
    else:
        for template in templates.get("templates", []):
            if not isinstance(template, Mapping):
                _issue(issues, "artifact template is not a mapping")
                continue
            values = template.get("placeholder_values")
            if not isinstance(values, Mapping) or values.get("sha256") != _SHA_PLACEHOLDER:
                _issue(issues, "artifact template must keep sha256 as a placeholder")

    return {
        "schema_version": "source_adapter_capture_action_kit_verifier_v1",
        "source_adapter_capture_action_kit_id": action_kit_id or "",
        "source_adapter_capture_setup_id": package.get("source_adapter_capture_setup_id", ""),
        "action_kit_status": package.get("action_kit_status", ""),
        "adapter_count": package.get("adapter_count", 0),
        "action_count": len(package.get("action_index", {}).get("actions", [])) if isinstance(package.get("action_index"), Mapping) else 0,
        "issue_count": len(issues),
        "issues": issues,
        "verified": not issues,
    }


if __name__ == "__main__":
    from source_adapter_capture_action_kit import build_source_adapter_capture_action_kit

    package = build_source_adapter_capture_action_kit(
        {"adapters": [{"adapter_id": "article", "artifact_roles": ["article_html_or_text"]}]}
    )
    result = verify_source_adapter_capture_action_kit(package)
    assert result["verified"] is True
    print("Source Adapter Capture Action Kit verifier self-test passed.")
