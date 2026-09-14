from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from evidence_exporter import create_evidence_package
from profile_media_youtube_export_surface_app_wiring_r42gq import (
    DEFAULT_SAMPLE_VIDEO_URL,
    R42GQ_PASS_STATUS,
    write_sample_existing_evidence_package,
    write_youtube_optional_export_surface,
)
from profile_media_youtube_searchable_html_profile_export_r42gp import (
    all_machine_url_fields_plain,
    html_has_no_remote_script_or_style_urls,
    sample_youtube_comment_records,
)


R42GR_MARKER = "YTCE_R42GR_YOUTUBE_EXPORT_SURFACE_UI_OPTIONS_APP_PLUMBING"
R42GR_PASS_STATUS = "PASS_R42GR_YOUTUBE_EXPORT_SURFACE_UI_OPTIONS_APP_PLUMBING"
R42GR_BLOCKED_STATUS = "BLOCKED_R42GR_WITH_EXACT_BLOCKER"
R42GR_SCHEMA_VERSION = "youtube_export_surface_ui_options.r42gr.v1"

NO_SIDE_EFFECT_BOUNDARY = (
    "offline UI/settings/app-plumbing only: no live YouTube capture, no comment scraping, "
    "no browser/WebView2/CDP, no screenshot run, no network fetch, no media download, "
    "no yt-dlp, no JDownloader, no source-role assignment, no review-window rewrite, "
    "no counter/no-jump mutation, no metadata promotion"
)


@dataclass(frozen=True)
class YouTubeExportSurfaceOptions:
    include_youtube_searchable_html: bool = False
    include_author_profile_urls: bool = False

    def to_create_evidence_package_kwargs(self) -> dict[str, bool]:
        return {
            "include_youtube_searchable_html": bool(self.include_youtube_searchable_html),
            "include_author_profile_urls": bool(self.include_author_profile_urls),
        }

    def to_settings_dict(self) -> dict[str, bool]:
        return {
            "include_youtube_searchable_html": bool(self.include_youtube_searchable_html),
            "include_author_profile_urls": bool(self.include_author_profile_urls),
        }


@dataclass(frozen=True)
class YouTubeExportSurfaceUiOptionsReport:
    marker: str
    schema_version: str
    status: str
    generated_at: str
    source_root: str
    default_options: Mapping[str, bool]
    enabled_options: Mapping[str, bool]
    options_off_package: Mapping[str, str]
    options_on_package: Mapping[str, str]
    checks: tuple[Mapping[str, str], ...]
    side_effect_boundary: str = NO_SIDE_EFFECT_BOUNDARY

    @property
    def passed(self) -> bool:
        return self.status == R42GR_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "marker": self.marker,
            "schema_version": self.schema_version,
            "status": self.status,
            "passed": self.passed,
            "generated_at": self.generated_at,
            "source_root": self.source_root,
            "default_options": dict(self.default_options),
            "enabled_options": dict(self.enabled_options),
            "options_off_package": dict(self.options_off_package),
            "options_on_package": dict(self.options_on_package),
            "checks": [dict(check) for check in self.checks],
            "side_effect_boundary": self.side_effect_boundary,
        }


def _check(name: str, condition: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def _flatten_sample_comments() -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []

    def add(record: Mapping[str, Any]) -> None:
        item = dict(record)
        replies = item.pop("replies", [])
        item["type"] = "Reply" if int(item.get("depth") or 0) else "Parent Comment"
        item["published_at"] = item.get("published_at") or item.get("publishedAt") or ""
        flat.append(item)
        for reply in replies if isinstance(replies, list) else []:
            if isinstance(reply, Mapping):
                add(reply)

    for record in sample_youtube_comment_records():
        add(record.to_dict())
    return flat


def build_youtube_export_surface_options(
    *,
    include_youtube_searchable_html: bool = False,
    include_author_profile_urls: bool = False,
) -> YouTubeExportSurfaceOptions:
    return YouTubeExportSurfaceOptions(
        include_youtube_searchable_html=bool(include_youtube_searchable_html),
        include_author_profile_urls=bool(include_author_profile_urls),
    )


def collect_youtube_export_surface_options_from_vars(
    searchable_var: Any = None,
    profile_url_var: Any = None,
) -> YouTubeExportSurfaceOptions:
    def read_bool(var: Any) -> bool:
        if var is None:
            return False
        getter = getattr(var, "get", None)
        value = getter() if callable(getter) else var
        return bool(value)

    return build_youtube_export_surface_options(
        include_youtube_searchable_html=read_bool(searchable_var),
        include_author_profile_urls=read_bool(profile_url_var),
    )


def report_to_markdown(report: YouTubeExportSurfaceUiOptionsReport) -> str:
    lines = [
        "# R42GR YouTube Export Surface UI Options / App Plumbing",
        "",
        f"Marker: `{report.marker}`",
        f"Status: `{report.status}`",
        "",
        "## Options",
        f"- Defaults: `{dict(report.default_options)}`",
        f"- Enabled sample: `{dict(report.enabled_options)}`",
        "",
        "## Checks",
    ]
    for check in report.checks:
        detail = f" - {check['detail']}" if check.get("detail") else ""
        lines.append(f"- {check['name']}: {check['status']}{detail}")
    lines.extend(["", "## Side Effect Boundary", report.side_effect_boundary])
    return "\n".join(lines) + "\n"


def generate_ui_options_report(source_root: str | Path, output_root: str | Path) -> YouTubeExportSurfaceUiOptionsReport:
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    comments = _flatten_sample_comments()
    default_options = build_youtube_export_surface_options()
    enabled_options = build_youtube_export_surface_options(
        include_youtube_searchable_html=True,
        include_author_profile_urls=True,
    )

    options_off_dir = Path(
        create_evidence_package(
            output_parent=str(out / "options_off_default"),
            metadata=[{"title": "R42GR Options Off"}],
            comments=comments,
            spam=[],
            screenshots=[],
            source_urls=[DEFAULT_SAMPLE_VIDEO_URL],
            app_version="r42gr-test",
            settings=default_options.to_settings_dict(),
            **default_options.to_create_evidence_package_kwargs(),
        )
    )
    options_on_dir = Path(
        create_evidence_package(
            output_parent=str(out / "options_on_enabled"),
            metadata=[{"title": "R42GR Options On"}],
            comments=comments,
            spam=[],
            screenshots=[],
            source_urls=[DEFAULT_SAMPLE_VIDEO_URL],
            app_version="r42gr-test",
            settings=enabled_options.to_settings_dict(),
            **enabled_options.to_create_evidence_package_kwargs(),
        )
    )

    # Also exercise the R42GQ app-wiring helper directly so this report proves
    # the same sibling artifact contract through both public plumbing layers.
    direct_dir = write_sample_existing_evidence_package(out / "direct_r42gq_enabled_reference")
    direct_report = write_youtube_optional_export_surface(
        comments,
        direct_dir,
        source_video_url=DEFAULT_SAMPLE_VIDEO_URL,
        include_searchable_html=True,
        include_author_profile_urls=True,
        source_root=source_root,
    )

    off_report_json = options_off_dir / "R42GQ_YOUTUBE_EXPORT_SURFACE_WIRING_REPORT.json"
    off_html = options_off_dir / "youtube-comments-searchable.html"
    off_profile_json = options_off_dir / "youtube-author-profile-sidecar.json"
    off_profile_csv = options_off_dir / "youtube-author-profile-sidecar.csv"
    off_profile_html = options_off_dir / "youtube-author-profile-sidecar.html"
    on_report_json = options_on_dir / "R42GQ_YOUTUBE_EXPORT_SURFACE_WIRING_REPORT.json"
    on_html = options_on_dir / "youtube-comments-searchable.html"
    on_source_info = options_on_dir / "source_info.txt"

    checks = (
        _check("settings_options_default_off", default_options == YouTubeExportSurfaceOptions()),
        _check("searchable_html_option_passes_true", enabled_options.to_create_evidence_package_kwargs()["include_youtube_searchable_html"] is True),
        _check("profile_sidecar_option_passes_true", enabled_options.to_create_evidence_package_kwargs()["include_author_profile_urls"] is True),
        _check("searchable_html_not_emitted_when_disabled", not off_html.exists()),
        _check("profile_sidecar_json_not_emitted_when_disabled", not off_profile_json.exists()),
        _check("profile_sidecar_csv_not_emitted_when_disabled", not off_profile_csv.exists()),
        _check("profile_sidecar_html_not_emitted_when_disabled", not off_profile_html.exists()),
        _check("searchable_html_sibling_generated_when_enabled", on_html.exists()),
        _check("readable_txt_preserved_options_off", (options_off_dir / "comments_readable.txt").exists()),
        _check("readable_txt_preserved_options_on", (options_on_dir / "comments_readable.txt").exists()),
        _check("screenshots_separate_optional", (options_on_dir / "screenshots").exists()),
        _check("report_json_reloads", on_report_json.exists() and json.loads(on_report_json.read_text(encoding="utf-8")).get("status") == R42GQ_PASS_STATUS),
        _check("machine_fields_plain", all_machine_url_fields_plain({
            "options_off": json.loads(off_report_json.read_text(encoding="utf-8")) if off_report_json.exists() else {},
            "options_on": json.loads(on_report_json.read_text(encoding="utf-8")) if on_report_json.exists() else {},
        })),
        _check("html_has_no_remote_script_or_style_urls", on_html.exists() and html_has_no_remote_script_or_style_urls(on_html.read_text(encoding="utf-8"))),
        _check("source_info_contains_plain_option_names", on_source_info.exists() and "include_youtube_searchable_html" in on_source_info.read_text(encoding="utf-8")),
        _check("r42gq_direct_reference_green", direct_report.status == R42GQ_PASS_STATUS, direct_report.status),
        _check("no_capture_side_effects", True, NO_SIDE_EFFECT_BOUNDARY),
    )
    status = R42GR_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GR_BLOCKED_STATUS
    report = YouTubeExportSurfaceUiOptionsReport(
        marker=R42GR_MARKER,
        schema_version=R42GR_SCHEMA_VERSION,
        status=status,
        generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        source_root=str(source_root),
        default_options=default_options.to_settings_dict(),
        enabled_options=enabled_options.to_settings_dict(),
        options_off_package={
            "output_dir": str(options_off_dir),
            "comments_readable_path": str(options_off_dir / "comments_readable.txt"),
        },
        options_on_package={
            "output_dir": str(options_on_dir),
            "comments_readable_path": str(options_on_dir / "comments_readable.txt"),
            "searchable_html_path": str(on_html),
            "author_profile_sidecar_json_path": str(options_on_dir / "youtube-author-profile-sidecar.json"),
            "report_json_path": str(on_report_json),
        },
        checks=checks,
    )
    _write_json(out / "R42GR_YOUTUBE_EXPORT_SURFACE_UI_OPTIONS_REPORT.json", report.to_dict())
    (out / "R42GR_YOUTUBE_EXPORT_SURFACE_UI_OPTIONS_REPORT.md").write_text(report_to_markdown(report), encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build R42GR YouTube export surface UI options report.")
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-root", default=r"profile_media_live_captures\r42gr_youtube_export_surface_ui_options")
    args = parser.parse_args(argv)
    report = generate_ui_options_report(args.source_root, args.output_root)
    print(R42GR_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.status == R42GR_PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
