from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

VERIFIER_SCHEMA_VERSION = "source_adapter_fixture_authoring_verifier_v1"

_REQUIRED_TOP_LEVEL = {
    "schema_version",
    "source_adapter_fixture_authoring_id",
    "adapter_count",
    "fixture_template_count",
    "adapter_packets",
    "template_index",
    "shared_stage_route_plan",
    "fixture_review_handoff",
    "operator_summary",
}

_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}


def _find_forbidden_path_fields(value: object, *, prefix: str = "root") -> list[str]:
    issues: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in _FORBIDDEN_PATH_FIELDS:
                issues.append(f"{prefix}.{key}")
            issues.extend(_find_forbidden_path_fields(child, prefix=f"{prefix}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            issues.extend(_find_forbidden_path_fields(child, prefix=f"{prefix}[{index}]"))
    return issues


def verify_source_adapter_fixture_authoring(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    missing = sorted(_REQUIRED_TOP_LEVEL.difference(package.keys()))
    if missing:
        issues.append(f"missing top-level fields: {', '.join(missing)}")
    if package.get("schema_version") != "source_adapter_fixture_authoring_package_v1":
        issues.append("unexpected schema_version")
    adapter_packets = package.get("adapter_packets")
    if not isinstance(adapter_packets, list) or not adapter_packets:
        issues.append("adapter_packets must be a non-empty array")
    else:
        template_total = 0
        for index, packet in enumerate(adapter_packets):
            if not isinstance(packet, Mapping):
                issues.append(f"adapter_packets[{index}] must be an object")
                continue
            if not packet.get("adapter_id"):
                issues.append(f"adapter_packets[{index}] missing adapter_id")
            templates = packet.get("fixture_templates")
            if not isinstance(templates, list) or not templates:
                issues.append(f"adapter_packets[{index}] has no fixture templates")
                continue
            template_total += len(templates)
            for template_index, template in enumerate(templates):
                if not isinstance(template, Mapping):
                    issues.append(f"adapter_packets[{index}].fixture_templates[{template_index}] must be an object")
                    continue
                basename = str(template.get("safe_template_basename") or "")
                if not basename or "/" in basename or "\\" in basename:
                    issues.append(f"unsafe template basename for adapter_packets[{index}].fixture_templates[{template_index}]")
        if package.get("fixture_template_count") != template_total:
            issues.append("fixture_template_count does not match adapter packet templates")
    if package.get("adapter_count") != len(adapter_packets or []):
        issues.append("adapter_count does not match adapter_packets")
    handoff = package.get("fixture_review_handoff")
    if isinstance(handoff, Mapping):
        if handoff.get("manual_or_live_actions_started") is not False:
            issues.append("fixture review handoff must not start manual/live actions")
        if handoff.get("live_network_default") is not False:
            issues.append("fixture review handoff live_network_default must be false")
    else:
        issues.append("fixture_review_handoff must be an object")
    operator_summary = package.get("operator_summary")
    if isinstance(operator_summary, Mapping):
        if operator_summary.get("manual_or_live_actions_started") is not False:
            issues.append("operator summary must not start manual/live actions")
        if operator_summary.get("live_network_default") is not False:
            issues.append("operator summary live_network_default must be false")
    else:
        issues.append("operator_summary must be an object")
    forbidden = _find_forbidden_path_fields(package)
    if forbidden:
        issues.append(f"forbidden local path fields present: {', '.join(forbidden[:5])}")
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "source_adapter_fixture_authoring_id": str(package.get("source_adapter_fixture_authoring_id", "")),
        "adapter_count": package.get("adapter_count", 0),
        "fixture_template_count": package.get("fixture_template_count", 0),
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
    }


def verify_source_adapter_fixture_authoring_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        return {
            "schema_version": VERIFIER_SCHEMA_VERSION,
            "source_adapter_fixture_authoring_id": "",
            "adapter_count": 0,
            "fixture_template_count": 0,
            "verified": False,
            "issue_count": 1,
            "issues": ["fixture authoring file must contain a JSON object"],
        }
    return verify_source_adapter_fixture_authoring(data)


if __name__ == "__main__":
    from source_adapter_fixture_authoring import build_source_adapter_fixture_authoring

    matrix = {
        "fixture_matrix": {
            "rows": [
                {
                    "adapter_id": "article",
                    "fixture_types": ["saved_article_html_or_text", "expected_pipeline_closeout_json"],
                    "shared_pipeline_stages": ["artifact_collection", "pipeline_closeout"],
                }
            ]
        }
    }
    result = verify_source_adapter_fixture_authoring(build_source_adapter_fixture_authoring(matrix))
    assert result["verified"], result
    print("Source Adapter Fixture Authoring verifier self-test passed.")
