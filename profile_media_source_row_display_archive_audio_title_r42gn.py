from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from source_resource_state import (
    ARCHIVE_SERVICE_ARCHIVE_TODAY,
    ARCHIVE_SERVICE_LOCAL_WEB_ARCHIVE,
    ARCHIVE_SERVICE_WAYBACK,
    ARCHIVE_STATUS_APPROVAL_REQUIRED,
    GLOBAL_PLAYER_LBC_EPISODE_URL,
    build_source_resource_row,
)
from source_twitter_compact_row import build_twitter_compact_row_state


R42GN_MARKER = "YTCE_R42GN_SOURCE_ROW_DISPLAY_ARCHIVE_AUDIO_TITLE_AUDIT"
R42GN_PASS_STATUS = "PASS_R42GN_SOURCE_ROW_DISPLAY_ARCHIVE_AUDIO_TITLE_AUDIT"
R42GN_BLOCKED_STATUS = "BLOCKED_R42GN_WITH_EXACT_BLOCKER"

BBC_TWITTER_STATUS_URL = "https://x.com/BBCr4today/status/2097217541416308845"
EXAMADDAORG_TWITTER_URL = "https://x.com/examaddaorg"
METRO_ARTICLE_URL = "https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/"


@dataclass(frozen=True)
class SourceRowDisplayAuditItem:
    name: str
    status: str
    details: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def twitter_archive_policy_summary(url: str = BBC_TWITTER_STATUS_URL) -> SourceRowDisplayAuditItem:
    row = build_source_resource_row(url)
    services = tuple(status.service_id for status in row.archive_statuses)
    return SourceRowDisplayAuditItem(
        name="twitter_x_archive_policy",
        status="pass"
        if ARCHIVE_SERVICE_WAYBACK not in services
        and ARCHIVE_SERVICE_ARCHIVE_TODAY in services
        and ARCHIVE_SERVICE_LOCAL_WEB_ARCHIVE in services
        else "fail",
        details={
            "canonical_url": row.canonical_url,
            "services": services,
            "archive_today_status": next((status.status for status in row.archive_statuses if status.service_id == ARCHIVE_SERVICE_ARCHIVE_TODAY), ""),
            "policy": "archive.ph/local metadata-only buttons are visible; Wayback is not shown for X/Twitter rows; no archive submission runs",
        },
    )


def twitter_display_summary(title: str) -> SourceRowDisplayAuditItem:
    row = build_source_resource_row(BBC_TWITTER_STATUS_URL, title=title)
    state = build_twitter_compact_row_state(row)
    return SourceRowDisplayAuditItem(
        name="twitter_x_compact_display",
        status="pass" if len(state.display_title) <= 72 and state.title_treatment == "compact_normal_weight_single_line" else "fail",
        details={
            "raw_title": row.title,
            "display_title": state.display_title,
            "archive_controls_visible": state.archive_controls_visible,
            "archive_controls_policy": state.archive_controls_policy,
            "settings_preserved": tuple(state.settings_keys),
        },
    )


def global_player_title_summary(url: str = GLOBAL_PLAYER_LBC_EPISODE_URL) -> SourceRowDisplayAuditItem:
    row = build_source_resource_row(url)
    method_tokens = ("yt_dlp_python_module", "py -m yt_dlp", "format 0", "native m4a", "sidecars")
    return SourceRowDisplayAuditItem(
        name="global_player_cached_title_and_method_metadata",
        status="pass"
        if "Tuesday, 08 September" in row.display_title
        and "Nick Ferrari" in row.display_title
        and all(token in row.provenance for token in method_tokens)
        else "fail",
        details={
            "canonical_url": row.canonical_url,
            "display_title": row.display_title,
            "comments_status": row.comments_status,
            "provenance": row.provenance,
            "warning_count": len(row.warnings),
            "network_or_download_actions": "none",
        },
    )


def metro_archive_policy_summary(url: str = METRO_ARTICLE_URL) -> SourceRowDisplayAuditItem:
    row = build_source_resource_row(url)
    services = tuple(status.service_id for status in row.archive_statuses)
    return SourceRowDisplayAuditItem(
        name="metro_webpage_archive_policy_preserved",
        status="pass"
        if (
            ARCHIVE_SERVICE_WAYBACK in services
            and ARCHIVE_SERVICE_ARCHIVE_TODAY in services
            and ARCHIVE_SERVICE_LOCAL_WEB_ARCHIVE in services
        )
        else "fail",
        details={
            "canonical_url": row.canonical_url,
            "services": services,
            "policy": "existing webpage/news Wayback/archive.ph/Local controls preserved",
        },
    )


def build_r42gn_audit_items() -> tuple[SourceRowDisplayAuditItem, ...]:
    return (
        twitter_display_summary(
            '"I think it carries a real risk of increased chances of attacks on the British Jewish community." Dr Peter Prinsley tells BBC Radio 4 Today.'
        ),
        twitter_archive_policy_summary(BBC_TWITTER_STATUS_URL),
        twitter_archive_policy_summary(EXAMADDAORG_TWITTER_URL),
        global_player_title_summary(GLOBAL_PLAYER_LBC_EPISODE_URL),
        metro_archive_policy_summary(METRO_ARTICLE_URL),
    )


def validate_r42gn_source_row_display_archive_audio_title() -> Mapping[str, Any]:
    items = build_r42gn_audit_items()
    failures = [item.name for item in items if item.status != "pass"]
    return {
        "marker": R42GN_MARKER,
        "status": R42GN_PASS_STATUS if not failures else R42GN_BLOCKED_STATUS,
        "failures": failures,
        "items": [item.to_dict() for item in items],
        "guardrails": {
            "live_capture": "not_run",
            "browser_launch": "not_run",
            "yt_dlp_execution": "not_run",
            "media_download": "not_run",
            "archive_submission": "not_run",
            "source_role_assignment": "not_changed",
            "counter_no_jump": "not_changed",
            "metadata_promotion": "none",
        },
    }


def write_report(report: Mapping[str, Any], output_root: str | Path) -> Path:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "R42GN_SOURCE_ROW_DISPLAY_ARCHIVE_AUDIO_TITLE_REPORT.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=R42GN_MARKER)
    parser.add_argument("--source-root", default=".")
    parser.add_argument(
        "--output-root",
        default="profile_media_live_captures/r42gn_source_row_display_archive_audio_title",
    )
    args = parser.parse_args(argv)
    report = validate_r42gn_source_row_display_archive_audio_title()
    report_path = write_report(report, Path(args.source_root) / args.output_root)
    print(R42GN_MARKER)
    print(report["status"])
    print(f"report={report_path}")
    return 0 if report["status"] == R42GN_PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(_main())
