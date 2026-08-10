from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Mapping

from source_msn_adapter_manifest import (
    MSN_SOURCE_ADAPTER_NAME,
    MsnSourceAdapterBundle,
    write_msn_source_adapter_bundle_json,
)
from source_msn_adapter_readiness import (
    READINESS_NOT_COMPLETE,
    READINESS_PARTIAL,
    READINESS_STRUCTURALLY_COMPLETE,
    MsnAdapterReadinessReport,
    evaluate_msn_source_adapter_readiness,
    write_msn_source_adapter_readiness_report,
)


MSN_SOURCE_ADAPTER_RELEASE_REPORT_SCHEMA_VERSION = "msn_source_adapter_release_report_v1"
RELEASE_STATUS_READY_FOR_MANUAL_LIVE_VALIDATION = "READY_FOR_MANUAL_LIVE_VALIDATION"
RELEASE_STATUS_NOT_READY = "NOT_READY"
RELEASE_STATUS_MANUAL_LIVE_VALIDATION_REQUIRED = "MANUAL_LIVE_VALIDATION_REQUIRED"


@dataclass(frozen=True)
class MsnSourceAdapterReleaseArea:
    name: str
    status: str
    summary: str
    required_for_confidence: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MsnSourceAdapterReleaseReport:
    schema_version: str = MSN_SOURCE_ADAPTER_RELEASE_REPORT_SCHEMA_VERSION
    adapter_name: str = MSN_SOURCE_ADAPTER_NAME
    release_status: str = RELEASE_STATUS_NOT_READY
    readiness_status: str = READINESS_NOT_COMPLETE
    areas: tuple[MsnSourceAdapterReleaseArea, ...] = ()
    output_paths: Mapping[str, str] = field(default_factory=dict)
    manual_live_validation_checklist: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    confidence_summary: str = ""
    manual_review_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def _readiness_dict(readiness: MsnAdapterReadinessReport | Mapping[str, Any]) -> Mapping[str, Any]:
    if hasattr(readiness, "to_dict") and callable(readiness.to_dict):
        return readiness.to_dict()
    return readiness


def _finding_detail(readiness_data: Mapping[str, Any], area: str) -> str:
    for finding in readiness_data.get("findings") or []:
        if isinstance(finding, Mapping) and finding.get("area") == area:
            return str(finding.get("detail") or "")
    return ""


def _area(name: str, status: str, summary: str, *, required: bool = True) -> MsnSourceAdapterReleaseArea:
    return MsnSourceAdapterReleaseArea(name=name, status=status, summary=summary, required_for_confidence=required)


def manual_live_validation_checklist() -> tuple[str, ...]:
    return (
        "Confirm the target MSN URL, capture time, access mode, and whether the article is an MSN-original or a reposted publisher article.",
        "Open the rendered-page.html backup locally and confirm title, publisher/source, author/date/read-time if available, hero media, visible body text, bullet points, and source/original URL are present or marked partial.",
        "Open local_viewer/open_local_viewer.cmd and confirm the viewer labels rendered HTML, WARC.GZ, strict WACZ, compatible WACZ, comments/profile exports, and media outputs honestly.",
        "Open rendered-page.warc.gz in ReplayWeb.page and record whether the article is visible, partial, or failed. Do not claim full replay unless manually observed.",
        "Do not claim strict WACZ success unless ReplayWeb-compatible validation proves it; keep strict WACZ labelled experimental/possibly unsupported.",
        "Run the MSN comments capture/export flow as operator-approved manual capture only; verify top/newest runs, nested replies, deleted placeholders, likes/dislikes, profile links, and profile account stats.",
        "Check comments/profile outputs in JSON, TXT, Markdown, HTML, and profile export formats. Confirm copy/plain text does not include metadata labels unless additional-info is enabled.",
        "Review media candidates: hero image, inline images, posters, OpenGraph/Twitter images, JSON-LD images, direct video URLs, HLS/DASH manifests, and blocked/blob/streamed media.",
        "For each downloaded media asset, confirm local path, size, SHA-256/hash, observed-on URL, visible credit, claimed source, and source-chain gap status.",
        "Where MSN reposts from The Independent or another outlet, keep MSN surface, republishing outlet, visible image/video credit, and original primary source status separate.",
        "Confirm source-role fields are claim/item scoped: article/publisher framing is secondary unless primary source is located; user comments are primary only for the commenter's own authored statement.",
        "Record any missing context, cropped/removed content, untranslated captions, unsupported video streams, agency/family/authority repetitions, and closed-loop reporting risks.",
    )


def build_msn_source_adapter_release_report(
    bundle: MsnSourceAdapterBundle | Mapping[str, Any],
    *,
    readiness: MsnAdapterReadinessReport | Mapping[str, Any] | None = None,
    output_paths: Mapping[str, str] | None = None,
) -> MsnSourceAdapterReleaseReport:
    readiness_report = readiness or evaluate_msn_source_adapter_readiness(bundle)  # type: ignore[arg-type]
    data = _readiness_dict(readiness_report)
    readiness_status = str(data.get("overall_status") or READINESS_NOT_COMPLETE)
    media_status = str(data.get("media_status") or READINESS_PARTIAL)
    areas = (
        _area("article_extraction", str(data.get("article_status") or "MISSING"), _finding_detail(data, "article_extraction")),
        _area("comments_profile_extraction", str(data.get("comments_status") or "MISSING"), _finding_detail(data, "comments_profile_extraction")),
        _area("offline_webpage_viewer", str(data.get("offline_viewer_status") or "MISSING"), _finding_detail(data, "offline_webpage_viewer")),
        _area("media_discovery_download", media_status, _finding_detail(data, "media_discovery_download")),
        _area("source_role_provenance", str(data.get("provenance_status") or "MISSING"), _finding_detail(data, "source_role_provenance")),
    )
    has_blocking = any(
        isinstance(finding, Mapping) and bool(finding.get("blocking"))
        for finding in (data.get("findings") or [])
    )
    if readiness_status == READINESS_STRUCTURALLY_COMPLETE and not has_blocking:
        release_status = RELEASE_STATUS_READY_FOR_MANUAL_LIVE_VALIDATION
        confidence = (
            "MSN adapter is structurally complete for article extraction, comments/profile extraction, offline archive/viewer linking, "
            "media registration, and source-role provenance. Manual live validation is still required before calling a specific live capture complete."
        )
    else:
        release_status = RELEASE_STATUS_NOT_READY
        confidence = "MSN adapter is not structurally complete yet; address blocking readiness findings before manual live validation."
    limitations = tuple(data.get("limitations") or ()) + (
        "This release report does not run browser automation, live capture, network media download, WARC replay, WACZ replay, or external archive submission.",
        "A PARTIAL media status can be acceptable for structural readiness when media candidates are recorded but no local media file was selected/downloaded.",
        "Manual live validation remains the final confidence step for real MSN pages because MSN markup, comments shadow DOM, publisher reposting, and video delivery can change.",
    )
    return MsnSourceAdapterReleaseReport(
        release_status=release_status,
        readiness_status=readiness_status,
        areas=areas,
        output_paths=dict(output_paths or {}),
        manual_live_validation_checklist=manual_live_validation_checklist(),
        limitations=limitations,
        confidence_summary=confidence,
        manual_review_required=True,
    )


def render_msn_source_adapter_release_markdown(report: MsnSourceAdapterReleaseReport | Mapping[str, Any]) -> str:
    data = report.to_dict() if hasattr(report, "to_dict") else report
    lines = [
        "# MSN Source Adapter Release Report",
        "",
        f"Schema version: `{data.get('schema_version')}`",
        f"Adapter: `{data.get('adapter_name')}`",
        f"Release status: `{data.get('release_status')}`",
        f"Readiness status: `{data.get('readiness_status')}`",
        "",
        "## Confidence summary",
        "",
        str(data.get("confidence_summary") or ""),
        "",
        "## Areas",
        "",
    ]
    for area in data.get("areas") or []:
        lines.append(f"- `{area.get('name')}` — `{area.get('status')}`: {area.get('summary')}")
    lines.extend(["", "## Manual live validation checklist", ""])
    for index, item in enumerate(data.get("manual_live_validation_checklist") or [], start=1):
        lines.append(f"{index}. {item}")
    lines.extend(["", "## Limitations", ""])
    for item in data.get("limitations") or []:
        lines.append(f"- {item}")
    if data.get("output_paths"):
        lines.extend(["", "## Output paths", ""])
        for key, value in data.get("output_paths", {}).items():
            lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines).rstrip() + "\n"


def write_msn_source_adapter_release_outputs(
    *,
    bundle: MsnSourceAdapterBundle,
    output_dir: str | Path,
    base_name: str = "msn-source-adapter-release",
) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    bundle_path = out / f"{base_name}-bundle.json"
    readiness_path = out / f"{base_name}-readiness.json"
    release_json_path = out / f"{base_name}-report.json"
    release_md_path = out / f"{base_name}-report.md"
    checklist_path = out / f"{base_name}-manual-live-validation.md"

    write_msn_source_adapter_bundle_json(bundle, bundle_path)
    readiness = evaluate_msn_source_adapter_readiness(bundle)
    write_msn_source_adapter_readiness_report(readiness, readiness_path)
    output_paths = {
        "bundle_json": str(bundle_path),
        "readiness_json": str(readiness_path),
        "release_report_json": str(release_json_path),
        "release_report_markdown": str(release_md_path),
        "manual_live_validation_markdown": str(checklist_path),
    }
    report = build_msn_source_adapter_release_report(bundle, readiness=readiness, output_paths=output_paths)
    release_json_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    release_md = render_msn_source_adapter_release_markdown(report)
    release_md_path.write_text(release_md, encoding="utf-8")
    checklist_path.write_text("# MSN Manual Live Validation Checklist\n\n" + "\n".join(f"{i}. {item}" for i, item in enumerate(report.manual_live_validation_checklist, start=1)) + "\n", encoding="utf-8")
    return output_paths
