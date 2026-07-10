from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Sequence

from source_adapters import AVAILABLE_SOURCE_ADAPTERS, SourceAdapter


REPORT_FORMATS = ("markdown", "text", "json")

STATUS_IMPLEMENTED = "implemented"
STATUS_FUTURE_CANDIDATE = "future_candidate"
STATUS_FUTURE_BACKEND = "future_backend"


@dataclass(frozen=True)
class SourceAdapterGapCategory:
    category_id: str
    display_name: str
    status: str
    current_adapter_ids: tuple[str, ...] = ()
    example_platforms: tuple[str, ...] = ()
    notes: str = ""
    recommended_next_step: str = ""


@dataclass(frozen=True)
class SourceAdapterGapAnalysis:
    categories: tuple[SourceAdapterGapCategory, ...]
    current_adapter_ids: tuple[str, ...]
    scope: str = (
        "local source adapter and preservation gap analysis only; no fetch, capture, "
        "network, provider, archive, browser, scraping, credential, or GUI behavior"
    )


FUTURE_PLATFORM_CATEGORIES: tuple[SourceAdapterGapCategory, ...] = (
    SourceAdapterGapCategory(
        category_id="social_video",
        display_name="Social video platforms",
        status=STATUS_FUTURE_CANDIDATE,
        example_platforms=("TikTok", "Instagram", "Facebook video"),
        notes="Future site-specific or site-family metadata skeletons only.",
        recommended_next_step="Pick one platform family and add metadata-only URL recognition tests first.",
    ),
    SourceAdapterGapCategory(
        category_id="text_microblogging",
        display_name="Text / microblogging platforms",
        status=STATUS_FUTURE_CANDIDATE,
        example_platforms=("Twitter/X", "Threads", "Mastodon/Fediverse"),
        notes="Public/private visibility and login/session boundaries must be explicit.",
        recommended_next_step="Start with metadata-only URL recognition and capability notes.",
    ),
    SourceAdapterGapCategory(
        category_id="community_forum",
        display_name="Community, forum, Q&A, and link aggregators",
        status=STATUS_FUTURE_CANDIDATE,
        example_platforms=("Reddit", "forums", "Q&A sites"),
        notes="Do not assume one generic forum scraper; site rules vary.",
        recommended_next_step="Add a specific adapter skeleton only after choosing a site family.",
    ),
    SourceAdapterGapCategory(
        category_id="review_platforms",
        display_name="Review platforms",
        status=STATUS_FUTURE_CANDIDATE,
        example_platforms=("Trustpilot", "Google Reviews", "Amazon reviews"),
        notes="Review exports have platform-specific visibility, pagination, and policy constraints.",
        recommended_next_step="Keep as gap-analysis metadata until a platform is selected.",
    ),
    SourceAdapterGapCategory(
        category_id="newsletter_sites",
        display_name="Newsletter / publication websites",
        status=STATUS_FUTURE_CANDIDATE,
        example_platforms=("Substack", "newsletter websites", "publication comments"),
        notes="Substack-style sites may have public pages, subscriber-only pages, and comment systems.",
        recommended_next_step="Consider a metadata-only Substack/newsletter URL-recognition skeleton later.",
    ),
    SourceAdapterGapCategory(
        category_id="workplace_chat",
        display_name="Workplace / chat communities",
        status=STATUS_FUTURE_CANDIDATE,
        example_platforms=("Discord", "Slack-style exports"),
        notes="Often requires user-authenticated export or manual import; avoid credential/session work.",
        recommended_next_step="Prefer manual import metadata before any integration.",
    ),
    SourceAdapterGapCategory(
        category_id="self_hosted_preservation",
        display_name="Self-hosted preservation backend",
        status=STATUS_FUTURE_BACKEND,
        example_platforms=("ArchiveBox-style local/self-hosted store",),
        notes=(
            "Future backend category for user-controlled preservation outputs such as HTML, PDF, PNG, "
            "TXT, JSON, WARC, media files, and SQLite-style metadata."
        ),
        recommended_next_step=(
            "Start with local-only preservation backend metadata/plans and manual import of already-created files."
        ),
    ),
)


def _category_for_adapter(adapter: SourceAdapter) -> SourceAdapterGapCategory:
    metadata = adapter.metadata
    return SourceAdapterGapCategory(
        category_id=adapter.source_name,
        display_name=metadata.display_name or adapter.source_name,
        status=STATUS_IMPLEMENTED,
        current_adapter_ids=(adapter.source_name,),
        example_platforms=(metadata.display_name or adapter.source_name,),
        notes=metadata.access_limitations,
        recommended_next_step="Keep metadata/reporting tests green before adding capture behavior.",
    )


def build_source_adapter_gap_analysis(
    adapters: Sequence[SourceAdapter] = AVAILABLE_SOURCE_ADAPTERS,
) -> SourceAdapterGapAnalysis:
    implemented = tuple(_category_for_adapter(adapter) for adapter in adapters)
    current_adapter_ids = tuple(adapter.source_name for adapter in adapters)
    return SourceAdapterGapAnalysis(
        categories=implemented + FUTURE_PLATFORM_CATEGORIES,
        current_adapter_ids=current_adapter_ids,
    )


def source_adapter_gap_analysis_to_dict(
    analysis: SourceAdapterGapAnalysis,
) -> dict[str, Any]:
    return {
        "current_adapter_ids": list(analysis.current_adapter_ids),
        "implemented_adapter_count": len(analysis.current_adapter_ids),
        "scope": analysis.scope,
        "categories": [
            {
                "category_id": category.category_id,
                "current_adapter_ids": list(category.current_adapter_ids),
                "display_name": category.display_name,
                "example_platforms": list(category.example_platforms),
                "notes": category.notes,
                "recommended_next_step": category.recommended_next_step,
                "status": category.status,
            }
            for category in analysis.categories
        ],
    }


def build_source_adapter_gap_analysis_markdown(
    analysis: SourceAdapterGapAnalysis,
) -> str:
    lines = [
        "# Source Adapter / Preservation Gap Analysis",
        "",
        "Local planning report only. This report does not fetch URLs, call providers, scrape platforms, capture screenshots, submit/check archives, store credentials, run ArchiveBox, download media, or wire into the GUI.",
        "",
        f"- Implemented adapter count: {len(analysis.current_adapter_ids)}",
        f"- Current adapters: {', '.join(analysis.current_adapter_ids) or 'none'}",
        "",
    ]

    for category in analysis.categories:
        lines.extend(
            [
                f"## {category.display_name}",
                "",
                f"- Category ID: {category.category_id}",
                f"- Status: {category.status}",
                f"- Current adapter IDs: {', '.join(category.current_adapter_ids) or 'none'}",
                f"- Example platforms: {', '.join(category.example_platforms) or 'none'}",
            ]
        )
        if category.notes:
            lines.append(f"- Notes: {category.notes}")
        if category.recommended_next_step:
            lines.append(f"- Recommended next step: {category.recommended_next_step}")
        lines.append("")

    return "\n".join(lines).rstrip()


def build_source_adapter_gap_analysis_text(
    analysis: SourceAdapterGapAnalysis,
) -> str:
    lines = [
        "Source adapter / preservation gap analysis",
        "Scope: local planning only; no fetch/capture/network/provider/archive/browser/scraping/credential/GUI behavior is performed.",
        f"Implemented adapter count: {len(analysis.current_adapter_ids)}",
        f"Current adapters: {', '.join(analysis.current_adapter_ids) or 'none'}",
    ]

    for category in analysis.categories:
        lines.extend(
            [
                "",
                f"{category.category_id} ({category.display_name})",
                f"status: {category.status}",
                f"current_adapter_ids: {', '.join(category.current_adapter_ids) or 'none'}",
                f"example_platforms: {', '.join(category.example_platforms) or 'none'}",
            ]
        )
        if category.notes:
            lines.append(f"notes: {category.notes}")
        if category.recommended_next_step:
            lines.append(f"recommended_next_step: {category.recommended_next_step}")

    return "\n".join(lines)


def render_source_adapter_gap_analysis(
    analysis: SourceAdapterGapAnalysis,
    *,
    output_format: str,
) -> str:
    if output_format == "markdown":
        return build_source_adapter_gap_analysis_markdown(analysis)
    if output_format == "text":
        return build_source_adapter_gap_analysis_text(analysis)
    if output_format == "json":
        return json.dumps(
            source_adapter_gap_analysis_to_dict(analysis),
            indent=2,
            sort_keys=True,
        )
    raise ValueError(f"unsupported output format: {output_format}")
