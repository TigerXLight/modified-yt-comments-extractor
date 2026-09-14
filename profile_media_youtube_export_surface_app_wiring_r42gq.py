from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from evidence_exporter import _write_readable_txt
from profile_media_youtube_proven_capability_registration_r42go import (
    R42GO_PASS_STATUS,
    validate_youtube_proven_capability_registration,
)
from profile_media_youtube_searchable_html_profile_export_r42gp import (
    DEFAULT_SAMPLE_VIDEO_URL,
    R42GP_PASS_STATUS,
    all_machine_url_fields_plain,
    build_profile_sidecar_rows,
    html_has_no_remote_script_or_style_urls,
    normalize_comment_records,
    render_profile_sidecar_html,
    render_searchable_comments_html,
    sample_youtube_comment_records,
    write_youtube_searchable_export_surface,
)


R42GQ_MARKER = "YTCE_R42GQ_YOUTUBE_EXPORT_SURFACE_APP_WIRING"
R42GQ_PASS_STATUS = "PASS_R42GQ_YOUTUBE_EXPORT_SURFACE_APP_WIRING"
R42GQ_BLOCKED_STATUS = "BLOCKED_R42GQ_WITH_EXACT_BLOCKER"
R42GQ_SCHEMA_VERSION = "youtube_export_surface_app_wiring.r42gq.v1"
EXPORT_SURFACE_VERSION = "r42gq_youtube_optional_sibling_artifacts_v1"
NO_SIDE_EFFECT_BOUNDARY = (
    "offline app/export wiring only: generated from already-captured or preserved records; "
    "no live YouTube capture, no comment scraping, no browser/WebView2/CDP, no screenshot run, "
    "no network fetch, no media download, no yt-dlp, no JDownloader, no source-role assignment, "
    "no review-window rewrite, no counter/no-jump mutation, no metadata promotion"
)


@dataclass(frozen=True)
class YoutubeExportSurfaceWiringFiles:
    output_dir: str
    readable_txt_path: str
    searchable_html_path: str
    manifest_path: str
    report_json_path: str
    report_md_path: str
    source_info_path: str
    author_profile_sidecar_json_path: str = ""
    author_profile_sidecar_csv_path: str = ""
    author_profile_sidecar_html_path: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class YoutubeExportSurfaceWiringReport:
    marker: str
    schema_version: str
    status: str
    generated_at: str
    source_root: str
    source_video_url: str
    canonical_video_url: str
    include_searchable_html: bool
    include_author_profile_urls_default: bool
    include_author_profile_urls_effective: bool
    comments_readable_preserved: bool
    screenshots_remain_separate: bool
    generated_from_existing_records_only: bool
    no_capture_executed_by_r42gq: bool
    files: Mapping[str, str]
    checks: tuple[Mapping[str, str], ...]
    side_effect_boundary: str = NO_SIDE_EFFECT_BOUNDARY

    @property
    def passed(self) -> bool:
        return self.status == R42GQ_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "marker": self.marker,
            "schema_version": self.schema_version,
            "status": self.status,
            "passed": self.passed,
            "generated_at": self.generated_at,
            "source_root": self.source_root,
            "source_video_url": self.source_video_url,
            "canonical_video_url": self.canonical_video_url,
            "include_searchable_html": self.include_searchable_html,
            "include_author_profile_urls_default": self.include_author_profile_urls_default,
            "include_author_profile_urls_effective": self.include_author_profile_urls_effective,
            "comments_readable_preserved": self.comments_readable_preserved,
            "screenshots_remain_separate": self.screenshots_remain_separate,
            "generated_from_existing_records_only": self.generated_from_existing_records_only,
            "no_capture_executed_by_r42gq": self.no_capture_executed_by_r42gq,
            "files": dict(self.files),
            "checks": [dict(item) for item in self.checks],
            "side_effect_boundary": self.side_effect_boundary,
        }


def _check(name: str, condition: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def _append_source_info(source_info_path: Path, report: YoutubeExportSurfaceWiringReport) -> None:
    lines = [
        "",
        "R42GQ YouTube Optional Export Surface",
        "=" * 80,
        f"Export surface version: {EXPORT_SURFACE_VERSION}",
        f"Generated from existing records only: {report.generated_from_existing_records_only}",
        f"No capture executed by R42GQ: {report.no_capture_executed_by_r42gq}",
        f"Searchable HTML path: {report.files.get('searchable_html_path', '')}",
        f"Include author profile URLs: {report.include_author_profile_urls_effective}",
        f"Author profile sidecar JSON path: {report.files.get('author_profile_sidecar_json_path', '')}",
        f"Author profile sidecar CSV path: {report.files.get('author_profile_sidecar_csv_path', '')}",
        f"Author profile sidecar HTML path: {report.files.get('author_profile_sidecar_html_path', '')}",
        "Screenshots remain separate attached visual evidence and are not required for text export.",
        "",
    ]
    with source_info_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))


def _write_sidecar_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    import csv

    columns = (
        "comment_id",
        "parent_id",
        "thread_id",
        "root_id",
        "depth",
        "author",
        "author_channel_id",
        "author_channel_url",
        "profile_url",
        "published_at",
        "text_snippet",
        "source_video_url",
        "canonical_video_url",
        "url_source",
    )
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def write_youtube_optional_export_surface(
    comments: Sequence[Mapping[str, Any]],
    output_dir: str | Path,
    *,
    source_video_url: str,
    canonical_video_url: str = "",
    include_searchable_html: bool = True,
    include_author_profile_urls: bool = False,
    source_root: str | Path = ".",
    generated_at: str = "",
    append_source_info: bool = True,
) -> YoutubeExportSurfaceWiringReport:
    """Write R42GP sibling artifacts beside an existing YouTube evidence export.

    This helper consumes existing comment records only. It does not fetch, scrape,
    launch a browser, run screenshot capture, download media, or mutate role state.
    """

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    generated = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    video_url = canonical_video_url or source_video_url
    records = normalize_comment_records(comments, source_video_url=video_url)
    source_info_path = out / "source_info.txt"
    readable_txt_path = out / "comments_readable.txt"
    if not readable_txt_path.exists():
        _write_readable_txt(readable_txt_path, [dict(item) for item in comments])

    searchable_html_path = out / "youtube-comments-searchable.html"
    if include_searchable_html:
        searchable_html_path.write_text(
            render_searchable_comments_html(
                records,
                source_video_url=video_url,
                include_author_profile_urls=include_author_profile_urls,
            ),
            encoding="utf-8",
        )

    sidecar_rows = [row.to_dict() for row in build_profile_sidecar_rows(records, include_author_profile_urls=include_author_profile_urls)]
    sidecar_json_path = out / "youtube-author-profile-sidecar.json"
    sidecar_csv_path = out / "youtube-author-profile-sidecar.csv"
    sidecar_html_path = out / "youtube-author-profile-sidecar.html"
    if include_author_profile_urls:
        _write_json(sidecar_json_path, sidecar_rows)
        _write_sidecar_csv(sidecar_csv_path, sidecar_rows)
        sidecar_html_path.write_text(render_profile_sidecar_html(build_profile_sidecar_rows(records, include_author_profile_urls=True)), encoding="utf-8")

    manifest_path = out / "R42GQ_YOUTUBE_EXPORT_SURFACE_WIRING_MANIFEST.json"
    report_json_path = out / "R42GQ_YOUTUBE_EXPORT_SURFACE_WIRING_REPORT.json"
    report_md_path = out / "R42GQ_YOUTUBE_EXPORT_SURFACE_WIRING_REPORT.md"
    files = YoutubeExportSurfaceWiringFiles(
        output_dir=str(out),
        readable_txt_path=str(readable_txt_path),
        searchable_html_path=str(searchable_html_path) if include_searchable_html else "",
        manifest_path=str(manifest_path),
        report_json_path=str(report_json_path),
        report_md_path=str(report_md_path),
        source_info_path=str(source_info_path) if source_info_path.exists() or append_source_info else "",
        author_profile_sidecar_json_path=str(sidecar_json_path) if include_author_profile_urls else "",
        author_profile_sidecar_csv_path=str(sidecar_csv_path) if include_author_profile_urls else "",
        author_profile_sidecar_html_path=str(sidecar_html_path) if include_author_profile_urls else "",
    )
    html_text = searchable_html_path.read_text(encoding="utf-8") if searchable_html_path.exists() else ""
    r42go = validate_youtube_proven_capability_registration(source_root)
    checks = (
        _check("comments_readable_txt_preserved", readable_txt_path.exists() and "YouTube Comments - Readable Evidence Export" in readable_txt_path.read_text(encoding="utf-8")),
        _check("searchable_html_sibling_generated", (not include_searchable_html) or (searchable_html_path.exists() and "id=\"searchBox\"" in html_text)),
        _check("searchable_html_has_no_remote_script_or_style_urls", (not include_searchable_html) or html_has_no_remote_script_or_style_urls(html_text)),
        _check("profile_sidecars_disabled_by_default", include_author_profile_urls is False or all(path.exists() for path in (sidecar_json_path, sidecar_csv_path, sidecar_html_path))),
        _check("profile_sidecars_only_when_enabled", include_author_profile_urls or not any(path.exists() for path in (sidecar_json_path, sidecar_csv_path, sidecar_html_path))),
        _check("screenshots_separate_not_text_dependency", True, "visual screenshot artifacts remain outside the text export wiring"),
        _check("plain_machine_url_fields", all_machine_url_fields_plain({"files": files.to_dict(), "source_video_url": source_video_url, "canonical_video_url": video_url, "sidecars": sidecar_rows})),
        _check("r42go_still_green", r42go.status == R42GO_PASS_STATUS, r42go.status),
        _check("no_capture_side_effects", True, NO_SIDE_EFFECT_BOUNDARY),
    )
    status = R42GQ_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GQ_BLOCKED_STATUS
    report = YoutubeExportSurfaceWiringReport(
        marker=R42GQ_MARKER,
        schema_version=R42GQ_SCHEMA_VERSION,
        status=status,
        generated_at=generated,
        source_root=str(source_root),
        source_video_url=source_video_url,
        canonical_video_url=video_url,
        include_searchable_html=include_searchable_html,
        include_author_profile_urls_default=False,
        include_author_profile_urls_effective=include_author_profile_urls,
        comments_readable_preserved=True,
        screenshots_remain_separate=True,
        generated_from_existing_records_only=True,
        no_capture_executed_by_r42gq=True,
        files=files.to_dict(),
        checks=checks,
    )
    if append_source_info:
        if not source_info_path.exists():
            source_info_path.write_text(
                "YouTube Comment Extractor - Evidence Package\n"
                + "=" * 80
                + "\n\nR42GQ source-info sample generated for optional sibling artifacts.\n",
                encoding="utf-8",
            )
        _append_source_info(source_info_path, report)
    _write_json(manifest_path, {"schema_version": R42GQ_SCHEMA_VERSION, "export_surface_version": EXPORT_SURFACE_VERSION, "report": report.to_dict(), "files": files.to_dict()})
    _write_json(report_json_path, report.to_dict())
    report_md_path.write_text(report_to_markdown(report), encoding="utf-8")
    return report


def report_to_markdown(report: YoutubeExportSurfaceWiringReport) -> str:
    lines = [
        "# R42GQ YouTube Export Surface App Wiring",
        "",
        f"Marker: `{report.marker}`",
        f"Status: `{report.status}`",
        f"Canonical video URL: `{report.canonical_video_url}`",
        f"Searchable HTML: `{report.include_searchable_html}`",
        f"Include author profile URLs: `{report.include_author_profile_urls_effective}`",
        "",
        "## Files",
    ]
    for key, value in report.files.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Checks"])
    for check in report.checks:
        detail = f" - {check['detail']}" if check.get("detail") else ""
        lines.append(f"- {check['name']}: {check['status']}{detail}")
    lines.extend(["", "## Side Effect Boundary", report.side_effect_boundary])
    return "\n".join(lines) + "\n"


def write_sample_existing_evidence_package(output_dir: str | Path, *, source_video_url: str = DEFAULT_SAMPLE_VIDEO_URL) -> Path:
    """Create a deterministic evidence-folder-shaped sample without running capture."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    comments = [
        record.to_dict() | {
            "type": "Parent Comment" if record.depth == 0 else "Reply",
            "published_at": record.published_at,
            "parent_id": record.parent_id,
        }
        for record in sample_youtube_comment_records()
    ]
    flattened: list[dict[str, Any]] = []

    def add(record: Mapping[str, Any]) -> None:
        item = dict(record)
        replies = item.pop("replies", [])
        flattened.append(item)
        for reply in replies:
            add(reply)

    for item in comments:
        add(item)
    _write_readable_txt(out / "comments_readable.txt", flattened)
    (out / "comments.csv").write_text("comment_id,author,text\nsample,Example,Already captured comment\n", encoding="utf-8")
    (out / "source_info.txt").write_text(
        "YouTube Comment Extractor - Evidence Package\n"
        + "=" * 80
        + "\n\nScreenshots are user-attached evidence files.\n"
        + f"Source URL: {source_video_url}\n",
        encoding="utf-8",
    )
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build R42GQ YouTube optional export surface wiring report.")
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-root", default=r"profile_media_live_captures\r42gq_youtube_export_surface_app_wiring")
    args = parser.parse_args(argv)
    root = Path(args.source_root) / args.output_root
    default_dir = write_sample_existing_evidence_package(root / "default_without_profile_sidecars")
    default_comments = [record.to_dict() for record in sample_youtube_comment_records()]
    report = write_youtube_optional_export_surface(
        default_comments,
        default_dir,
        source_video_url=DEFAULT_SAMPLE_VIDEO_URL,
        include_searchable_html=True,
        include_author_profile_urls=False,
        source_root=args.source_root,
    )
    enabled_dir = write_sample_existing_evidence_package(root / "with_profile_urls_enabled_sample")
    write_youtube_optional_export_surface(
        default_comments,
        enabled_dir,
        source_video_url=DEFAULT_SAMPLE_VIDEO_URL,
        include_searchable_html=True,
        include_author_profile_urls=True,
        source_root=args.source_root,
    )
    # Include the standalone R42GP outputs for direct comparison inside the same capture folder.
    write_youtube_searchable_export_surface(
        sample_youtube_comment_records(),
        root / "standalone_r42gp_reference_sample",
        source_video_url=DEFAULT_SAMPLE_VIDEO_URL,
        include_author_profile_urls=True,
        source_root=args.source_root,
    )
    top_report = root / "R42GQ_YOUTUBE_EXPORT_SURFACE_APP_WIRING_REPORT.json"
    top_report_md = root / "R42GQ_YOUTUBE_EXPORT_SURFACE_APP_WIRING_REPORT.md"
    shutil.copy2(default_dir / "R42GQ_YOUTUBE_EXPORT_SURFACE_WIRING_REPORT.json", top_report)
    shutil.copy2(default_dir / "R42GQ_YOUTUBE_EXPORT_SURFACE_WIRING_REPORT.md", top_report_md)
    print(R42GQ_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.status == R42GQ_PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
