from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

VERIFIER_SCHEMA_VERSION = "source_adapter_fixture_review_verifier_v1"

_REQUIRED_TOP_LEVEL = {
    "schema_version",
    "source_adapter_fixture_review_id",
    "source_adapter_fixture_authoring_id",
    "adapter_count",
    "fixture_count",
    "review_status",
    "issue_count",
    "issues",
    "adapter_reviews",
    "fixture_registry",
    "fixture_pipeline_handoff",
    "fixture_review_report",
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


def _unsafe_basename(value: object) -> bool:
    text = str(value or "")
    return not text or "/" in text or "\\" in text or text in {".", ".."}


def verify_source_adapter_fixture_review(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    missing = sorted(_REQUIRED_TOP_LEVEL.difference(package.keys()))
    if missing:
        issues.append(f"missing top-level fields: {', '.join(missing)}")
    if package.get("schema_version") != "source_adapter_fixture_review_package_v1":
        issues.append("unexpected schema_version")
    fixtures = None
    registry = package.get("fixture_registry")
    if isinstance(registry, Mapping):
        fixtures = registry.get("fixtures")
        if not isinstance(fixtures, list) or not fixtures:
            issues.append("fixture_registry.fixtures must be a non-empty array")
        else:
            for index, row in enumerate(fixtures):
                if not isinstance(row, Mapping):
                    issues.append(f"fixture_registry.fixtures[{index}] must be an object")
                    continue
                if _unsafe_basename(row.get("template_safe_basename")):
                    issues.append(f"fixture_registry.fixtures[{index}] has unsafe template basename")
                source_artifact = str(row.get("source_artifact_safe_basename") or "")
                if source_artifact and _unsafe_basename(source_artifact):
                    issues.append(f"fixture_registry.fixtures[{index}] has unsafe source artifact basename")
    else:
        issues.append("fixture_registry must be an object")
    if package.get("fixture_count") != len(fixtures or []):
        issues.append("fixture_count does not match fixture registry")
    adapter_reviews = package.get("adapter_reviews")
    if not isinstance(adapter_reviews, list) or not adapter_reviews:
        issues.append("adapter_reviews must be a non-empty array")
    elif package.get("adapter_count") != len(adapter_reviews):
        issues.append("adapter_count does not match adapter_reviews")
    package_issues = package.get("issues")
    if not isinstance(package_issues, list):
        issues.append("issues must be an array")
    elif package.get("issue_count") != len(package_issues):
        issues.append("issue_count does not match issues")
    review_status = package.get("review_status")
    if review_status not in {"PASSED", "BLOCKED"}:
        issues.append("review_status must be PASSED or BLOCKED")
    elif review_status == "PASSED" and package.get("issue_count") != 0:
        issues.append("PASSED review must have zero issues")
    handoff = package.get("fixture_pipeline_handoff")
    if isinstance(handoff, Mapping):
        if handoff.get("manual_or_live_actions_started") is not False:
            issues.append("pipeline handoff must not start manual/live actions")
        if handoff.get("live_network_default") is not False:
            issues.append("pipeline handoff live_network_default must be false")
    else:
        issues.append("fixture_pipeline_handoff must be an object")
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
        "source_adapter_fixture_review_id": str(package.get("source_adapter_fixture_review_id", "")),
        "source_adapter_fixture_authoring_id": str(package.get("source_adapter_fixture_authoring_id", "")),
        "adapter_count": package.get("adapter_count", 0),
        "fixture_count": package.get("fixture_count", 0),
        "review_status": str(package.get("review_status", "")),
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
    }


def verify_source_adapter_fixture_review_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        return {
            "schema_version": VERIFIER_SCHEMA_VERSION,
            "source_adapter_fixture_review_id": "",
            "source_adapter_fixture_authoring_id": "",
            "adapter_count": 0,
            "fixture_count": 0,
            "review_status": "",
            "verified": False,
            "issue_count": 1,
            "issues": ["fixture review file must contain a JSON object"],
        }
    return verify_source_adapter_fixture_review(data)


if __name__ == "__main__":
    from source_adapter_fixture_review import build_source_adapter_fixture_review

    authoring = {
        "source_adapter_fixture_authoring_id": "source_adapter_fixture_authoring.example",
        "template_index": {
            "template_rows": [
                {
                    "adapter_id": "article",
                    "fixture_type": "saved_article_html_or_text",
                    "artifact_role": "article_html_or_text",
                    "operator_supplied_file_required": True,
                    "safe_template_basename": "article.01.saved_article_html_or_text.template.json",
                }
            ]
        },
        "shared_stage_route_plan": {"adapters": [{"adapter_id": "article", "shared_pipeline_stages": ["artifact_collection"]}]},
    }
    authored = {
        "fixtures": [
            {
                "adapter_id": "article",
                "fixture_type": "saved_article_html_or_text",
                "template_safe_basename": "article.01.saved_article_html_or_text.template.json",
                "source_artifact_safe_basename": "article.fixture.html",
                "source_artifact_sha256": "c" * 64,
                "expected_assertions": {},
            }
        ]
    }
    result = verify_source_adapter_fixture_review(build_source_adapter_fixture_review(authoring, authored))
    assert result["verified"], result
    print("Source Adapter Fixture Review verifier self-test passed.")
