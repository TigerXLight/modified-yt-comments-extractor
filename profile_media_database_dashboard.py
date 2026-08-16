"""Dashboard summaries for Profile/Media Database mode.

V76A turns the read-only V75W/V75X/V75Y/V75Z foundations into a compact
workbench dashboard model.  The dashboard is deliberately built from explicit
batch JSON files or an already-built in-memory index.  It is not a filesystem
crawler and it does not mutate case folders.

The dashboard is intended for the future main Database workbench area after the
left sidebar toggle is switched to DATABASE mode.  It summarizes cases, sources,
profiles, review flags, source-role/source-bucket counts, and claim/currentness
facets while preserving the existing safety model.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_database import utc_now_iso
from profile_media_database_index import (
    ProfileMediaDatabaseIndex,
    build_database_index_from_batch_json_files,
    build_database_index_from_payloads,
)

PROFILE_MEDIA_DATABASE_DASHBOARD_SCHEMA_VERSION = "profile-media-database-dashboard-v76a"


@dataclass(frozen=True)
class ProfileMediaDashboardMetric:
    """A single top-level metric for a Database workbench dashboard."""

    key: str
    label: str
    value: int
    severity: str = "info"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaDashboardFacet:
    """One counted facet row, such as source bucket or source role."""

    facet_type: str
    value: str
    count: int
    review_relevant: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaDashboardReviewLane:
    """A dashboard lane for records needing manual review."""

    lane_id: str
    title: str
    count: int
    severity: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaDashboard:
    """Read-only dashboard snapshot for the Profile/Media Database workbench."""

    database_root: str
    metrics: tuple[ProfileMediaDashboardMetric, ...]
    facets: tuple[ProfileMediaDashboardFacet, ...]
    review_lanes: tuple[ProfileMediaDashboardReviewLane, ...]
    cases: tuple[str, ...]
    unique_profile_names: tuple[str, ...]
    schema_version: str = PROFILE_MEDIA_DATABASE_DASHBOARD_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    status: str = "success"
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "status": self.status,
            "database_root": self.database_root,
            "metric_count": len(self.metrics),
            "metrics": [metric.to_dict() for metric in self.metrics],
            "facet_count": len(self.facets),
            "facets": [facet.to_dict() for facet in self.facets],
            "review_lane_count": len(self.review_lanes),
            "review_lanes": [lane.to_dict() for lane in self.review_lanes],
            "case_count": len(self.cases),
            "cases": list(self.cases),
            "unique_profile_count": len(self.unique_profile_names),
            "unique_profile_names": list(self.unique_profile_names),
            "folder_scan_performed": self.folder_scan_performed,
            "folder_creation_performed": self.folder_creation_performed,
            "folder_move_performed": self.folder_move_performed,
            "folder_rename_performed": self.folder_rename_performed,
            "file_copy_performed": self.file_copy_performed,
            "file_write_performed": self.file_write_performed,
            "media_download_performed": self.media_download_performed,
            "automatic_classification_performed": self.automatic_classification_performed,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
            "warnings": list(self.warnings),
            "warning_count": len(self.warnings),
        }


def _unknown(value: str) -> bool:
    return not value or "UNKNOWN" in value.upper()


def _counter_facets(facet_type: str, counter: Counter[str], *, unknown_review: bool = False) -> list[ProfileMediaDashboardFacet]:
    facets: list[ProfileMediaDashboardFacet] = []
    for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0].lower())):
        display = value or "UNKNOWN"
        is_unknown = _unknown(display)
        facets.append(
            ProfileMediaDashboardFacet(
                facet_type=facet_type,
                value=display,
                count=count,
                review_relevant=bool(unknown_review and is_unknown),
                notes="needs manual review" if unknown_review and is_unknown else "",
            )
        )
    return facets


def build_dashboard_from_index(index: ProfileMediaDatabaseIndex) -> ProfileMediaDashboard:
    """Build a read-only dashboard from an already-compiled explicit index."""

    unique_profiles = tuple(sorted({row.canonical_name for row in index.profiles if row.canonical_name}))
    parser_warning_count = sum(len(row.parser_warnings) for row in index.profiles)
    source_chain_gap_count = sum(1 for row in index.sources if row.source_chain_gap)
    disputed_framing_count = sum(1 for row in index.sources if row.disputed_framing)
    unknown_source_role_count = sum(1 for row in index.sources if _unknown(row.source_role))
    unknown_claim_basis_count = sum(1 for row in index.sources if _unknown(row.claim_basis))

    metrics = (
        ProfileMediaDashboardMetric("cases", "Cases", len(index.cases)),
        ProfileMediaDashboardMetric("sources", "Sources", len(index.sources)),
        ProfileMediaDashboardMetric("profile_rows", "Profile rows", len(index.profiles)),
        ProfileMediaDashboardMetric("unique_profiles", "Unique global profiles", len(unique_profiles)),
        ProfileMediaDashboardMetric("source_chain_gaps", "Source-chain gaps", source_chain_gap_count, "high" if source_chain_gap_count else "info"),
        ProfileMediaDashboardMetric("disputed_framing", "Disputed framing", disputed_framing_count, "medium" if disputed_framing_count else "info"),
        ProfileMediaDashboardMetric("unknown_source_roles", "Unknown source roles", unknown_source_role_count, "medium" if unknown_source_role_count else "info"),
        ProfileMediaDashboardMetric("parser_warnings", "Profile parser warnings", parser_warning_count, "low" if parser_warning_count else "info"),
    )

    facets: list[ProfileMediaDashboardFacet] = []
    facets.extend(_counter_facets("source_bucket", Counter(row.source_bucket for row in index.sources)))
    facets.extend(_counter_facets("source_role", Counter(row.source_role for row in index.sources), unknown_review=True))
    facets.extend(_counter_facets("claim_basis", Counter(row.claim_basis for row in index.sources), unknown_review=True))
    facets.extend(_counter_facets("currentness_status", Counter(row.currentness_status for row in index.sources)))
    facets.extend(_counter_facets("profile_source_bucket", Counter(row.source_bucket for row in index.profiles)))

    review_lanes = (
        ProfileMediaDashboardReviewLane(
            "source_chain_gaps",
            "Source-chain gaps",
            source_chain_gap_count,
            "high" if source_chain_gap_count else "none",
            "Original source is missing, uncited, or cannot yet be located.",
        ),
        ProfileMediaDashboardReviewLane(
            "disputed_framing",
            "Disputed framing",
            disputed_framing_count,
            "medium" if disputed_framing_count else "none",
            "Original author/uploader disputes, corrects, or clarifies publisher framing/context.",
        ),
        ProfileMediaDashboardReviewLane(
            "unknown_source_roles",
            "Unknown source roles",
            unknown_source_role_count,
            "medium" if unknown_source_role_count else "none",
            "Source role needs manual primary/secondary/tertiary classification.",
        ),
        ProfileMediaDashboardReviewLane(
            "unknown_claim_bases",
            "Unknown claim basis",
            unknown_claim_basis_count,
            "medium" if unknown_claim_basis_count else "none",
            "Claim basis needs manual review.",
        ),
        ProfileMediaDashboardReviewLane(
            "parser_warnings",
            "Profile parser warnings",
            parser_warning_count,
            "low" if parser_warning_count else "none",
            "Profile text blocks have missing or malformed fields.",
        ),
    )
    return ProfileMediaDashboard(
        database_root=index.database_root,
        metrics=metrics,
        facets=tuple(facets),
        review_lanes=review_lanes,
        cases=tuple(sorted(set(index.cases))),
        unique_profile_names=unique_profiles,
        warnings=index.warnings,
    )


def build_dashboard_from_payloads(payloads: Iterable[Mapping[str, Any]]) -> ProfileMediaDashboard:
    """Build a dashboard from explicit in-memory batch payloads only."""

    return build_dashboard_from_index(build_database_index_from_payloads(payloads))


def build_dashboard_from_batch_json_files(paths: Iterable[str | Path]) -> ProfileMediaDashboard:
    """Build a dashboard from explicit batch JSON files only."""

    return build_dashboard_from_index(build_database_index_from_batch_json_files(paths))


def render_dashboard_text(dashboard: ProfileMediaDashboard) -> str:
    """Render a compact dashboard for logs, CLI proof, and future UI panels."""

    lines = [
        "Profile/Media Database Dashboard",
        f"Status: {dashboard.status}",
        f"Database root: {dashboard.database_root}",
        "Folder scan performed: false",
        "Folder creation performed: false",
        "Folder move performed: false",
        "Folder rename performed: false",
        "File copy performed: false",
        "File write performed: false",
        "Media download performed: false",
        "Automatic classification performed: false",
        "Sensitive identifier inference performed: false",
        "",
        "Metrics:",
    ]
    for metric in dashboard.metrics:
        suffix = f" ({metric.severity})" if metric.severity and metric.severity != "info" else ""
        lines.append(f"- {metric.label}: {metric.value}{suffix}")
    lines.extend(["", "Review lanes:"])
    for lane in dashboard.review_lanes:
        lines.append(f"- {lane.title}: {lane.count} [{lane.severity}]")
    lines.extend(["", "Facets:"])
    if not dashboard.facets:
        lines.append("- none")
    for facet in dashboard.facets:
        marker = " review" if facet.review_relevant else ""
        lines.append(f"- {facet.facet_type}: {facet.value} = {facet.count}{marker}")
    return "\n".join(lines)


def dashboard_payload(dashboard: ProfileMediaDashboard, *, include_text: bool = False) -> dict[str, Any]:
    """Return JSON-safe dashboard payload."""

    data = dashboard.to_dict()
    if include_text:
        data["dashboard_text"] = render_dashboard_text(dashboard)
    return data
