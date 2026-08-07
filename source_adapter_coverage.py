from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "source_adapter_coverage_v1"

PIPELINE_STAGES: tuple[dict[str, str], ...] = (
    {"stage_id": "source_discovery", "label": "Source discovery", "shared_module": "source_adapter_coverage"},
    {"stage_id": "lightweight_browser_capture", "label": "Lightweight in-app browser capture", "shared_module": "lightweight_in_app_browser_capture"},
    {"stage_id": "artifact_collection", "label": "Explicit artifact collection", "shared_module": "source_artifact_collection"},
    {"stage_id": "content_extraction", "label": "Article/content extraction", "shared_module": "source_content_extraction"},
    {"stage_id": "comments_extraction", "label": "Comments/replies extraction", "shared_module": "source_comment_extraction"},
    {"stage_id": "capture_bundle", "label": "Capture bundle", "shared_module": "source_capture_bundle"},
    {"stage_id": "total_export_package", "label": "Total Export package", "shared_module": "source_total_export_package"},
    {"stage_id": "evidence_queue", "label": "Evidence Queue integration", "shared_module": "source_evidence_queue"},
    {"stage_id": "evidence_review", "label": "Evidence Review package/decision", "shared_module": "source_evidence_review"},
    {"stage_id": "approved_release", "label": "Approved release package", "shared_module": "source_approved_release"},
    {"stage_id": "release_index", "label": "Release index/export bundle", "shared_module": "source_release_index"},
    {"stage_id": "release_audit", "label": "Release audit/traceability", "shared_module": "source_release_audit"},
    {"stage_id": "archive_handoff", "label": "Manual archive handoff", "shared_module": "source_archive_handoff"},
    {"stage_id": "archive_result_intake", "label": "Manual archive result intake", "shared_module": "source_archive_result_intake"},
    {"stage_id": "archive_review", "label": "Archive review package/decision", "shared_module": "source_archive_review"},
)

PIPELINE_STAGE_IDS = tuple(stage["stage_id"] for stage in PIPELINE_STAGES)

LIGHTWEIGHT_BROWSER_CAPABILITIES: tuple[dict[str, Any], ...] = (
    {
        "capability_id": "operator_url_load",
        "description": "Open one explicit operator-supplied URL in the embedded/browser shell.",
        "requires_approval": True,
        "live_network_by_default": False,
    },
    {
        "capability_id": "render_wait",
        "description": "Wait for a bounded operator-chosen render delay before artifact capture.",
        "requires_approval": True,
        "live_network_by_default": False,
    },
    {
        "capability_id": "dom_snapshot",
        "description": "Save DOM text/snapshot from the currently loaded page as an explicit artifact.",
        "requires_approval": True,
        "live_network_by_default": False,
    },
    {
        "capability_id": "screenshot_capture",
        "description": "Save a viewport/full-page screenshot as an explicit artifact.",
        "requires_approval": True,
        "live_network_by_default": False,
    },
    {
        "capability_id": "shadow_root_operator_snippet",
        "description": "Expose a named manual DevTools/browser snippet for shadow-root comments when required.",
        "requires_approval": True,
        "live_network_by_default": False,
    },
)

DEFAULT_ARTIFACT_ROLES = (
    "article_html_or_text",
    "comments_json_or_text",
    "dom_snapshot",
    "screenshot",
    "metadata_json",
    "archive_receipt_json",
)

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


def _stable_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)


def _digest(value: Any, length: int = 12) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()[:length]


def _safe_id(value: str, *, fallback: str = "adapter") -> str:
    candidate = _SAFE_ID_RE.sub("_", str(value or "").strip()).strip("._-")
    return candidate or fallback


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _normalised_strings(value: Any) -> list[str]:
    output: list[str] = []
    for item in _as_list(value):
        text = str(item or "").strip()
        if text and text not in output:
            output.append(text)
    return output


@dataclass(frozen=True)
class SourceAdapterSpec:
    adapter_id: str
    display_name: str
    source_kind: str = "web"
    domains: tuple[str, ...] = ()
    url_patterns: tuple[str, ...] = ()
    capture_surfaces: tuple[str, ...] = ()
    artifact_roles: tuple[str, ...] = DEFAULT_ARTIFACT_ROLES
    implemented_stages: tuple[str, ...] = ()
    extraction_notes: tuple[str, ...] = ()
    requires_lightweight_browser: bool = True
    operator_only: bool = True

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SourceAdapterSpec":
        adapter_id = _safe_id(str(data.get("adapter_id") or data.get("id") or data.get("name") or "adapter"))
        display_name = str(data.get("display_name") or data.get("name") or adapter_id).strip() or adapter_id
        implemented = tuple(stage for stage in _normalised_strings(data.get("implemented_stages")) if stage in PIPELINE_STAGE_IDS)
        artifact_roles = tuple(_normalised_strings(data.get("artifact_roles")) or list(DEFAULT_ARTIFACT_ROLES))
        return cls(
            adapter_id=adapter_id,
            display_name=display_name,
            source_kind=str(data.get("source_kind") or "web").strip() or "web",
            domains=tuple(_normalised_strings(data.get("domains") or data.get("site_domains"))),
            url_patterns=tuple(_normalised_strings(data.get("url_patterns"))),
            capture_surfaces=tuple(_normalised_strings(data.get("capture_surfaces") or data.get("surfaces"))),
            artifact_roles=artifact_roles,
            implemented_stages=implemented,
            extraction_notes=tuple(_normalised_strings(data.get("extraction_notes") or data.get("notes"))),
            requires_lightweight_browser=bool(data.get("requires_lightweight_browser", True)),
            operator_only=bool(data.get("operator_only", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "display_name": self.display_name,
            "source_kind": self.source_kind,
            "domains": list(self.domains),
            "url_patterns": list(self.url_patterns),
            "capture_surfaces": list(self.capture_surfaces),
            "artifact_roles": list(self.artifact_roles),
            "implemented_stages": list(self.implemented_stages),
            "extraction_notes": list(self.extraction_notes),
            "requires_lightweight_browser": self.requires_lightweight_browser,
            "operator_only": self.operator_only,
        }


@dataclass(frozen=True)
class SourceAdapterCoverageReport:
    coverage_id: str
    adapters: tuple[SourceAdapterSpec, ...]
    stage_matrix: tuple[dict[str, Any], ...]
    shared_implementation_plan: tuple[dict[str, Any], ...]
    lightweight_browser_plan: dict[str, Any]
    adapter_work_items: tuple[dict[str, Any], ...]
    operator_summary: dict[str, Any]
    issue_list: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "coverage_id": self.coverage_id,
            "coverage_strategy": "one_framework_many_adapters",
            "adapter_count": len(self.adapters),
            "adapters": [adapter.to_dict() for adapter in self.adapters],
            "stage_matrix": list(self.stage_matrix),
            "shared_implementation_plan": list(self.shared_implementation_plan),
            "lightweight_browser_plan": self.lightweight_browser_plan,
            "adapter_work_items": list(self.adapter_work_items),
            "operator_summary": self.operator_summary,
            "issue_count": len(self.issue_list),
            "issues": list(self.issue_list),
        }


def load_adapter_specs(path: str | Path) -> list[SourceAdapterSpec]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "adapters" in raw:
        raw_specs = raw["adapters"]
    else:
        raw_specs = raw
    if isinstance(raw_specs, Mapping):
        raw_specs = [raw_specs]
    if not isinstance(raw_specs, list):
        raise ValueError("adapter spec must be a JSON object, a JSON list, or an object with an 'adapters' list")
    specs = [SourceAdapterSpec.from_mapping(item) for item in raw_specs if isinstance(item, Mapping)]
    if not specs:
        raise ValueError("adapter spec did not contain any usable adapters")
    return specs


def build_source_adapter_coverage(
    adapter_specs: Sequence[SourceAdapterSpec | Mapping[str, Any]],
    *,
    include_lightweight_browser: bool = True,
    existing_shared_stages: Iterable[str] | None = None,
) -> SourceAdapterCoverageReport:
    adapters = tuple(spec if isinstance(spec, SourceAdapterSpec) else SourceAdapterSpec.from_mapping(spec) for spec in adapter_specs)
    if not adapters:
        raise ValueError("at least one source adapter is required")

    shared_stage_set = {stage for stage in (existing_shared_stages or PIPELINE_STAGE_IDS) if stage in PIPELINE_STAGE_IDS}
    issue_list: list[str] = []
    adapter_ids: set[str] = set()
    for adapter in adapters:
        if adapter.adapter_id in adapter_ids:
            issue_list.append(f"duplicate adapter_id: {adapter.adapter_id}")
        adapter_ids.add(adapter.adapter_id)
        if not adapter.domains and adapter.source_kind == "web":
            issue_list.append(f"{adapter.adapter_id}: web adapter has no domain metadata")
        if not adapter.artifact_roles:
            issue_list.append(f"{adapter.adapter_id}: no artifact roles declared")

    stage_matrix: list[dict[str, Any]] = []
    for stage in PIPELINE_STAGES:
        stage_id = stage["stage_id"]
        adapters_missing = [adapter.adapter_id for adapter in adapters if stage_id not in adapter.implemented_stages]
        stage_matrix.append(
            {
                "stage_id": stage_id,
                "label": stage["label"],
                "shared_module": stage["shared_module"],
                "coverage_mode": "shared_framework",
                "implemented_by_shared_stage": stage_id in shared_stage_set,
                "adapters_requiring_mapping": adapters_missing,
                "adapter_specific_module_required": False,
            }
        )

    shared_implementation_plan = tuple(
        {
            "stage_id": stage["stage_id"],
            "shared_module": stage["shared_module"],
            "action": "use_or_extend_shared_stage_contract",
            "reason": "avoid repeating MSN-sized implementation slices for each source adapter",
            "per_adapter_work": "metadata mapping and fixture coverage only",
        }
        for stage in PIPELINE_STAGES
    )

    browser_plan = build_lightweight_browser_plan(adapters, enabled=include_lightweight_browser)
    adapter_work_items = tuple(build_adapter_work_items(adapters))
    operator_summary = {
        "status": "PLANNED_SHARED_FRAMEWORK",
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "per_adapter_strategy": "adapter_specs_plus_shared_pipeline_stages",
        "next_actions": [
            "Add adapter specs for each source rather than cloning MSN modules.",
            "Route each source through the shared lightweight browser/artifact/extraction/review/release contracts.",
            "Only create adapter-specific code when a site has a genuinely unique extraction surface.",
        ],
    }
    coverage_id = "source_adapter_coverage." + _digest({"adapters": [a.to_dict() for a in adapters], "browser": browser_plan})
    return SourceAdapterCoverageReport(
        coverage_id=coverage_id,
        adapters=adapters,
        stage_matrix=tuple(stage_matrix),
        shared_implementation_plan=shared_implementation_plan,
        lightweight_browser_plan=browser_plan,
        adapter_work_items=adapter_work_items,
        operator_summary=operator_summary,
        issue_list=tuple(issue_list),
    )


def build_lightweight_browser_plan(adapters: Sequence[SourceAdapterSpec], *, enabled: bool = True) -> dict[str, Any]:
    browser_required = enabled and any(adapter.requires_lightweight_browser for adapter in adapters)
    return {
        "schema_version": "lightweight_in_app_browser_plan_v1",
        "enabled": bool(enabled),
        "required_by_any_adapter": browser_required,
        "execution_mode": "operator_approved_manual_only",
        "live_network_default": False,
        "approval_required_before_navigation": True,
        "capabilities": list(LIGHTWEIGHT_BROWSER_CAPABILITIES),
        "adapter_bindings": [
            {
                "adapter_id": adapter.adapter_id,
                "display_name": adapter.display_name,
                "domains": list(adapter.domains),
                "capture_surfaces": list(adapter.capture_surfaces),
                "uses_lightweight_browser": bool(enabled and adapter.requires_lightweight_browser),
                "artifact_roles": list(adapter.artifact_roles),
            }
            for adapter in adapters
        ],
    }


def build_adapter_work_items(adapters: Sequence[SourceAdapterSpec]) -> list[dict[str, Any]]:
    work_items: list[dict[str, Any]] = []
    for adapter in adapters:
        missing_stages = [stage for stage in PIPELINE_STAGE_IDS if stage not in adapter.implemented_stages]
        work_items.append(
            {
                "adapter_id": adapter.adapter_id,
                "display_name": adapter.display_name,
                "work_mode": "adapter_spec_mapping",
                "adapter_specific_module_required": False,
                "missing_stage_count": len(missing_stages),
                "missing_stages": missing_stages,
                "required_fixture_types": [
                    "saved_article_html_or_text",
                    "saved_comments_json_or_text",
                    "expected_extraction_json",
                    "expected_total_export_package_json",
                    "expected_review_release_archive_json",
                ],
                "browser_support": "shared_lightweight_browser_plan" if adapter.requires_lightweight_browser else "not_required_by_spec",
            }
        )
    return work_items


def coverage_report_to_json(report: SourceAdapterCoverageReport) -> str:
    return _stable_json(report.to_dict()) + "\n"
