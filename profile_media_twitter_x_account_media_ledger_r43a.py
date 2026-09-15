from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

R43A_MARKER = "YTCE_R43A_TWITTER_X_ACCOUNT_MEDIA_LEDGER_DATE_FOLDER_EXPORT_MAP"
R43A_PASS_STATUS = "PASS_R43A_TWITTER_X_ACCOUNT_MEDIA_LEDGER_DATE_FOLDER_EXPORT_MAP"
R43A_BLOCKED_STATUS = "BLOCKED_R43A_TWITTER_X_ACCOUNT_MEDIA_LEDGER_DATE_FOLDER_EXPORT_MAP"
R43A_SCHEMA_VERSION = "twitter_x_account_media_ledger_date_folder_export_map.r43a.v1"
R43A_DEFAULT_OUTPUT_ROOT = "source_exports/twitter_x"
R43A_REPORT_ROOT = "profile_media_live_captures/r43a_twitter_x_account_media_ledger_date_folder_export_map"


@dataclass(frozen=True)
class TwitterXAccountMediaItemR43A:
    media_id: str
    media_class: str
    source_url: str = ""
    media_url: str = ""
    local_path: str = ""
    filename: str = ""
    mime_type: str = ""
    width: int = 0
    height: int = 0
    duration_seconds: float = 0.0
    byte_status: str = "metadata_only_review_required"
    provenance: str = ""
    warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TwitterXAccountRecordR43A:
    record_id: str
    record_type: str
    source_url: str
    visible_text: str = ""
    visible_timestamp: str = ""
    capture_timestamp: str = ""
    author_handle: str = ""
    author_display_name: str = ""
    account_handle: str = ""
    original_post_id: str = ""
    reposted_by_handle: str = ""
    repost_context: Mapping[str, Any] = field(default_factory=dict)
    static_screenshot_path: str = ""
    media_items: tuple[TwitterXAccountMediaItemR43A, ...] = ()
    review_strings: tuple[str, ...] = ()
    observed_order: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["media_items"] = [item.to_dict() if hasattr(item, "to_dict") else _to_jsonable(item) for item in self.media_items]
        data["repost_context"] = dict(self.repost_context or {})
        return _to_jsonable(data)


@dataclass(frozen=True)
class TwitterXAccountMediaLedgerWriteResultR43A:
    marker: str
    schema_version: str
    status: str
    account_handle: str
    capture_timestamp: str
    output_root: str
    account_capture_dir: str
    account_record_path: str
    manifest_path: str
    account_timeline_path: str
    media_index_path: str
    progress_events_path: str
    review_strings_path: str
    record_count: int
    media_count: int
    screenshot_count: int
    date_folders: tuple[str, ...]
    post_folder_count: int
    side_effect_flags: Mapping[str, bool]
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R43A_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43AReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    ledger_result: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R43A_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [dict(check) for check in self.checks],
            "generated_at": self.generated_at,
            "ledger_result": _to_jsonable(self.ledger_result),
            "marker": self.marker,
            "schema_version": self.schema_version,
            "side_effect_flags": dict(self.side_effect_flags),
            "status": self.status,
        }


class TwitterXAccountMediaLedgerExporterR43A:
    """Account-level Twitter/X media ledger writer.

    This is a local Python/app-layer export map, not a WebView2 runner. It
    consumes post/repost records, screenshot receipts, and media metadata/local
    files observed by previous lanes. It writes an account_record.md index plus
    date/post/repost folders. It performs no remote media download, no hidden X
    API scraping, no cookie/token extraction, no challenge bypass, no source-role
    checks, and no review-window rewrite.
    """

    def __init__(self, output_root: str | Path = R43A_DEFAULT_OUTPUT_ROOT) -> None:
        self.output_root = Path(output_root)

    def write(self, records: Iterable[Mapping[str, Any] | TwitterXAccountRecordR43A], *, account_handle: str = "", capture_timestamp: str = "") -> TwitterXAccountMediaLedgerWriteResultR43A:
        return write_twitter_x_account_media_ledger_r43a(records, output_root=self.output_root, account_handle=account_handle, capture_timestamp=capture_timestamp)


def build_twitter_x_account_media_ledger_exporter_r43a(output_root: str | Path = R43A_DEFAULT_OUTPUT_ROOT) -> TwitterXAccountMediaLedgerExporterR43A:
    return TwitterXAccountMediaLedgerExporterR43A(output_root=output_root)


def write_twitter_x_account_media_ledger_r43a(
    records: Iterable[Mapping[str, Any] | TwitterXAccountRecordR43A],
    *,
    output_root: str | Path = R43A_DEFAULT_OUTPUT_ROOT,
    account_handle: str = "",
    capture_timestamp: str = "",
) -> TwitterXAccountMediaLedgerWriteResultR43A:
    rows = [_coerce_record(row, index=i) for i, row in enumerate(records or (), start=1)]
    capture_ts = _safe_ts(capture_timestamp) or _now_ts()
    handle = _safe_handle(account_handle or _first_non_empty(row.account_handle for row in rows) or "unknown_account")
    account_root = Path(output_root) / handle
    capture_dir = account_root / f"account_capture_{capture_ts}"
    dates_dir = capture_dir / "dates"
    capture_dir.mkdir(parents=True, exist_ok=True)
    dates_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    manifest_records: list[dict[str, Any]] = []
    timeline_rows: list[dict[str, Any]] = []
    media_index: list[dict[str, Any]] = []
    progress_events: list[dict[str, Any]] = []
    review_lines: list[str] = []
    date_folders: set[str] = set()
    screenshot_count = 0
    media_count = 0
    post_folder_count = 0

    sorted_rows = sorted(rows, key=lambda row: (_date_folder_for_record(row), row.observed_order or 0, row.record_id))
    for row in sorted_rows:
        date_folder = _date_folder_for_record(row)
        date_folders.add(date_folder)
        record_dir = dates_dir / date_folder / _record_folder_name(row)
        media_dir = record_dir / "media"
        image_dir = media_dir / "images"
        video_dir = media_dir / "videos"
        manifest_dir = media_dir / "manifests"
        segment_dir = media_dir / "segments"
        replies_dir = record_dir / "replies"
        for folder in (image_dir, video_dir, manifest_dir, segment_dir, replies_dir):
            folder.mkdir(parents=True, exist_ok=True)

        if _clean(row.static_screenshot_path):
            screenshot_target, copied = _copy_receipt_file(row.static_screenshot_path, record_dir / "static_screenshot", default_suffix=".png")
            if copied:
                screenshot_count += 1
            else:
                warnings.append(f"static screenshot was recorded as receipt only for {row.record_id}")
        else:
            screenshot_target = record_dir / "static_screenshot_missing.txt"
            screenshot_target.write_text("No static screenshot file was supplied for this record.\n", encoding="utf-8")
        screenshot_rel = _rel(capture_dir, screenshot_target)

        copied_media: list[dict[str, Any]] = []
        for item_index, item in enumerate(row.media_items or (), start=1):
            target_dir = _media_target_dir(item, image_dir=image_dir, video_dir=video_dir, manifest_dir=manifest_dir, segment_dir=segment_dir)
            preferred_name = item.filename or _filename_from_url(item.media_url or item.source_url) or f"media_{item_index:03d}{_extension_for_item(item)}"
            media_target, copied = _copy_or_url_receipt(item.local_path, target_dir / _safe_filename(preferred_name), item)
            media_payload = item.to_dict()
            media_payload.update(
                {
                    "account_handle": handle,
                    "record_id": row.record_id,
                    "record_type": row.record_type,
                    "visible_date_folder": date_folder,
                    "record_folder": _rel(capture_dir, record_dir),
                    "local_export_path": _rel(capture_dir, media_target),
                    "copied_local_bytes": bool(copied),
                    "remote_download_performed_by_r43a": False,
                }
            )
            copied_media.append(media_payload)
            media_index.append(media_payload)
            media_count += 1

        record_payload = row.to_dict()
        record_payload.update(
            {
                "schema_version": R43A_SCHEMA_VERSION,
                "marker": R43A_MARKER,
                "account_handle": handle,
                "capture_timestamp": capture_ts,
                "visible_date_folder": date_folder,
                "record_folder": _rel(capture_dir, record_dir),
                "static_screenshot": screenshot_rel,
                "media_folder": _rel(capture_dir, media_dir),
                "media_items": copied_media,
                "side_effect_flags": build_r43a_side_effect_flags(),
            }
        )
        _write_json(record_dir / "post.json", record_payload)
        if row.record_type == "repost" or row.original_post_id:
            _write_json(record_dir / "repost_context.json", _to_jsonable(row.repost_context or {"original_post_id": row.original_post_id, "reposted_by_handle": row.reposted_by_handle}))
        _write_post_markdown(record_dir / "post.md", row=row, handle=handle, date_folder=date_folder, capture_dir=capture_dir, record_dir=record_dir, screenshot_rel=screenshot_rel, copied_media=copied_media)

        timeline_row = {
            "schema_version": R43A_SCHEMA_VERSION,
            "marker": R43A_MARKER,
            "account_handle": handle,
            "record_id": row.record_id,
            "record_type": row.record_type,
            "source_url": _plain_url(row.source_url),
            "visible_timestamp": row.visible_timestamp,
            "capture_timestamp": row.capture_timestamp or capture_ts,
            "visible_date_folder": date_folder,
            "record_folder": _rel(capture_dir, record_dir),
            "post_markdown": _rel(capture_dir, record_dir / "post.md"),
            "post_json": _rel(capture_dir, record_dir / "post.json"),
            "static_screenshot": screenshot_rel,
            "media_folder": _rel(capture_dir, media_dir),
            "media_count": len(row.media_items or ()),
            "review_string_count": len(row.review_strings or ()),
        }
        timeline_rows.append(timeline_row)
        manifest_records.append(timeline_row)
        review_lines.extend(_review_lines_for_row(row, date_folder=date_folder, record_dir=_rel(capture_dir, record_dir)))
        progress_events.append(
            {
                "event": "record_folder_written",
                "record_id": row.record_id,
                "record_type": row.record_type,
                "visible_date_folder": date_folder,
                "record_folder": _rel(capture_dir, record_dir),
                "media_count": len(row.media_items or ()),
                "remote_download_performed_by_r43a": False,
            }
        )
        post_folder_count += 1

    date_folder_list = tuple(_sort_dates(date_folders))
    manifest = {
        "schema_version": R43A_SCHEMA_VERSION,
        "marker": R43A_MARKER,
        "status": R43A_PASS_STATUS,
        "account_handle": handle,
        "capture_timestamp": capture_ts,
        "account_capture_dir": str(capture_dir),
        "account_record_path": str(capture_dir / "account_record.md"),
        "record_count": len(rows),
        "media_count": media_count,
        "screenshot_count": screenshot_count,
        "date_folders": list(date_folder_list),
        "records": manifest_records,
        "side_effect_flags": build_r43a_side_effect_flags(),
        "folder_policy": build_r43a_folder_policy(),
        "warnings": warnings,
    }
    _write_json(capture_dir / "manifest.json", manifest)
    _write_json(capture_dir / "media_index.json", media_index)
    _write_jsonl(capture_dir / "account_timeline.ndjson", timeline_rows)
    _write_jsonl(capture_dir / "progress_events.ndjson", progress_events)
    (capture_dir / "review_strings.txt").write_text("\n".join(review_lines).rstrip() + ("\n" if review_lines else ""), encoding="utf-8")
    _write_account_record_markdown(capture_dir / "account_record.md", manifest=manifest, timeline_rows=timeline_rows, media_index=media_index)

    return TwitterXAccountMediaLedgerWriteResultR43A(
        marker=R43A_MARKER,
        schema_version=R43A_SCHEMA_VERSION,
        status=R43A_PASS_STATUS,
        account_handle=handle,
        capture_timestamp=capture_ts,
        output_root=str(output_root),
        account_capture_dir=str(capture_dir),
        account_record_path=str(capture_dir / "account_record.md"),
        manifest_path=str(capture_dir / "manifest.json"),
        account_timeline_path=str(capture_dir / "account_timeline.ndjson"),
        media_index_path=str(capture_dir / "media_index.json"),
        progress_events_path=str(capture_dir / "progress_events.ndjson"),
        review_strings_path=str(capture_dir / "review_strings.txt"),
        record_count=len(rows),
        media_count=media_count,
        screenshot_count=screenshot_count,
        date_folders=date_folder_list,
        post_folder_count=post_folder_count,
        side_effect_flags=build_r43a_side_effect_flags(),
        warnings=tuple(warnings),
    )


def build_r43a_folder_policy() -> dict[str, Any]:
    return {
        "marker": R43A_MARKER,
        "schema_version": R43A_SCHEMA_VERSION,
        "account_layout": "source_exports/twitter_x/<handle>/account_capture_<timestamp>",
        "single_whole_record_document": "account_record.md",
        "date_folder_rule": "visible post date first; fallback to capture date; unknown_date only when both are unavailable",
        "post_folder_rule": "dates/<date>/post_<post_id> for posts and dates/<date>/repost_<repost_id>__original_<original_post_id> for reposts",
        "media_folder_rule": "media/images, media/videos, media/manifests, media/segments under each post/repost folder",
        "static_screenshot_rule": "static_screenshot.* inside each post/repost folder, linked from both post.md and account_record.md",
        "directional_links": True,
        "stores_remote_candidates_as_receipts_when_no_local_file": True,
        "remote_downloads_performed_by_ledger": False,
    }


def build_r43a_side_effect_flags() -> dict[str, bool]:
    return {
        "r43a_account_media_ledger_written": True,
        "remote_media_download_performed_by_r43a": False,
        "network_actions_performed": False,
        "browser_session_started": False,
        "webview2_session_started_by_r43a": False,
        "hidden_x_api_scraping_performed": False,
        "login_automation_performed": False,
        "cookie_or_token_extraction_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "paywall_or_access_control_bypass_performed": False,
        "source_role_interface_loop_invoked": False,
        "source_role_checks_performed": False,
        "source_role_assignment_performed": False,
        "review_window_dependency_invoked": False,
        "review_window_rewrite_performed": False,
        "review_window_stays_separate": True,
        "youtube_capture_engine_changed": False,
    }


def build_report(output_root: str | Path = R43A_REPORT_ROOT) -> R43AReport:
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    fixture_root = out / "fixture_files"
    fixture_root.mkdir(parents=True, exist_ok=True)
    image = fixture_root / "image_001.jpg"
    video = fixture_root / "video_001.mp4"
    screenshot_1 = fixture_root / "post_static.png"
    screenshot_2 = fixture_root / "repost_static.png"
    for path, data in ((image, b"R43A_IMAGE_BYTES\n"), (video, b"R43A_VIDEO_BYTES\n"), (screenshot_1, b"R43A_SCREENSHOT_ONE\n"), (screenshot_2, b"R43A_SCREENSHOT_TWO\n")):
        path.write_bytes(data)
    records = (
        TwitterXAccountRecordR43A(
            account_handle="example", author_handle="example", author_display_name="Example Account",
            record_id="1111111111111111111", record_type="post", source_url="https://x.com/example/status/1111111111111111111",
            visible_text="A media post with an image and video.", visible_timestamp="2026-09-14T12:00:00Z", capture_timestamp="2026-09-14T12:05:00Z",
            static_screenshot_path=str(screenshot_1),
            media_items=(
                TwitterXAccountMediaItemR43A(media_id="img1", media_class="image", media_url="https://pbs.twimg.com/media/example.jpg?format=jpg&name=large", local_path=str(image), filename="example_image.jpg", mime_type="image/jpeg", provenance="R42GZ independent fast Media WebView2 lane"),
                TwitterXAccountMediaItemR43A(media_id="vid1", media_class="video", media_url="https://video.twimg.com/ext_tw_video/111/pu/vid/720x720/example.mp4", local_path=str(video), filename="example_video.mp4", mime_type="video/mp4", provenance="R42GZ independent fast Media WebView2 lane"),
            ),
            review_strings=("A media post with an image and video.",), observed_order=1,
        ),
        TwitterXAccountRecordR43A(
            account_handle="example", author_handle="other_author", author_display_name="Other Author",
            record_id="2222222222222222222", original_post_id="9999999999999999999", reposted_by_handle="example", record_type="repost",
            source_url="https://x.com/other_author/status/9999999999999999999", visible_text="Reposted media record with manifest receipt.",
            visible_timestamp="2026-09-15 09:30", capture_timestamp="2026-09-15T09:35:00Z", static_screenshot_path=str(screenshot_2),
            media_items=(TwitterXAccountMediaItemR43A(media_id="manifest1", media_class="manifest", media_url="https://video.twimg.com/ext_tw_video/999/pu/pl/manifest.m3u8?tag=16", filename="manifest.m3u8", mime_type="application/x-mpegURL", provenance="R42GZ independent fast Media WebView2 lane", warning="metadata-only remote candidate"),),
            review_strings=("Reposted media record with manifest receipt.",), observed_order=2,
        ),
    )
    result = write_twitter_x_account_media_ledger_r43a(records, output_root=out / "source_exports" / "twitter_x", account_handle="example", capture_timestamp="20260914T000000Z")
    result_dict = result.to_dict()
    capture_dir = Path(result.account_capture_dir)
    account_record = Path(result.account_record_path).read_text(encoding="utf-8")
    manifest = _read_json(Path(result.manifest_path), {})
    media_index = _read_json(Path(result.media_index_path), [])
    checks = (
        _check("account_capture_layout_created", capture_dir.is_dir() and (capture_dir / "dates" / "2026-09-14").is_dir() and (capture_dir / "dates" / "2026-09-15").is_dir()),
        _check("single_whole_account_record_document_links_date_folders", "account_record.md" in result.account_record_path and "dates/2026-09-14/" in account_record and "dates/2026-09-15/" in account_record),
        _check("post_and_repost_folders_written", (capture_dir / "dates" / "2026-09-14" / "post_1111111111111111111" / "post.md").is_file() and (capture_dir / "dates" / "2026-09-15" / "repost_2222222222222222222__original_9999999999999999999" / "post.md").is_file()),
        _check("static_screenshot_links_written", "static_screenshot" in account_record and (capture_dir / "dates" / "2026-09-14" / "post_1111111111111111111" / "static_screenshot.png").is_file()),
        _check("media_folders_and_index_written", (capture_dir / "media_index.json").is_file() and len(media_index) == 3 and "media/images" in account_record and "media/videos" in account_record and "media/manifests" in account_record),
        _check("date_attribution_rule_visible_then_capture", manifest.get("date_folders") == ["2026-09-14", "2026-09-15"]),
        _check("remote_candidates_are_receipts_not_downloads", any(str(item.get("local_export_path", "")).endswith(".url.txt") for item in media_index) and all(item.get("remote_download_performed_by_r43a") is False for item in media_index)),
        _check("review_strings_exported", Path(result.review_strings_path).is_file() and "Reposted media record" in Path(result.review_strings_path).read_text(encoding="utf-8")),
        _check("no_forbidden_side_effects", all(result.side_effect_flags.get(key) is False for key in ("remote_media_download_performed_by_r43a", "network_actions_performed", "browser_session_started", "webview2_session_started_by_r43a", "hidden_x_api_scraping_performed", "cookie_or_token_extraction_performed", "captcha_or_challenge_bypass_performed", "source_role_checks_performed", "source_role_assignment_performed", "review_window_dependency_invoked", "review_window_rewrite_performed", "youtube_capture_engine_changed"))),
        _check("plain_machine_urls", _machine_urls_are_plain(result_dict) and _machine_urls_are_plain(manifest) and _machine_urls_are_plain(media_index)),
    )
    status = R43A_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43A_BLOCKED_STATUS
    report = R43AReport(R43A_MARKER, R43A_SCHEMA_VERSION, datetime.now(timezone.utc).isoformat(), status, checks, result_dict, result.side_effect_flags)
    write_report(report, out)
    return report


def write_report(report: R43AReport, output_root: str | Path = R43A_REPORT_ROOT) -> None:
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "R43A_TWITTER_X_ACCOUNT_MEDIA_LEDGER_DATE_FOLDER_EXPORT_MAP_REPORT.json", report.to_dict())
    lines = ["# R43A Twitter/X Account Media Ledger And Date-Folder Export Map Report", "", f"- marker: `{report.marker}`", f"- status: `{report.status}`", f"- schema: `{report.schema_version}`", "", "## Checks"]
    for check in report.checks:
        lines.append(f"- {check.get('status')}: {check.get('name')} {check.get('detail') or ''}".rstrip())
    lines.extend(["", "## Model", "- Writes a single `account_record.md` index for the whole Twitter/X account capture.", "- Routes posts, reposts, screenshots, and media receipts into ordered date folders.", "- Each post/repost has its own folder with `post.md`, `post.json`, static screenshot receipt, and media subfolders.", "- Images and videos can be copied into the same post/repost folder tree when local bytes already exist.", "- Remote candidates are represented as receipt files only; the ledger performs no remote media download.", "- This local ledger layer is separate from WebView2, source-role review, and the review window."])
    (out / "R43A_TWITTER_X_ACCOUNT_MEDIA_LEDGER_DATE_FOLDER_EXPORT_MAP_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _coerce_record(row: Mapping[str, Any] | TwitterXAccountRecordR43A, *, index: int) -> TwitterXAccountRecordR43A:
    if isinstance(row, TwitterXAccountRecordR43A):
        return row if row.observed_order else TwitterXAccountRecordR43A(**{**row.to_dict(), "media_items": tuple(row.media_items), "review_strings": tuple(row.review_strings), "observed_order": index})
    data = dict(row or {})
    media = tuple(_coerce_media_item(item, index=i) for i, item in enumerate(data.get("media_items") or data.get("media") or (), start=1))
    return TwitterXAccountRecordR43A(record_id=_clean(data.get("record_id") or data.get("post_id") or data.get("status_id") or f"record_{index:06d}"), record_type=_safe_record_type(data.get("record_type") or data.get("type") or ("repost" if data.get("original_post_id") else "post")), source_url=_plain_url(data.get("source_url") or data.get("url") or data.get("canonical_url") or ""), visible_text=_clean(data.get("visible_text") or data.get("text") or data.get("body") or ""), visible_timestamp=_clean(data.get("visible_timestamp") or data.get("timestamp") or data.get("created_at") or ""), capture_timestamp=_clean(data.get("capture_timestamp") or data.get("captured_at") or ""), author_handle=_safe_handle(data.get("author_handle") or data.get("handle") or ""), author_display_name=_clean(data.get("author_display_name") or data.get("display_name") or ""), account_handle=_safe_handle(data.get("account_handle") or data.get("account") or ""), original_post_id=_clean(data.get("original_post_id") or data.get("retweeted_status_id") or ""), reposted_by_handle=_safe_handle(data.get("reposted_by_handle") or data.get("retweeter_handle") or ""), repost_context=dict(data.get("repost_context") or {}), static_screenshot_path=_clean(data.get("static_screenshot_path") or data.get("screenshot_path") or ""), media_items=media, review_strings=tuple(_clean(item) for item in (data.get("review_strings") or ()) if _clean(item)), observed_order=int(data.get("observed_order") or index))


def _coerce_media_item(item: Mapping[str, Any] | TwitterXAccountMediaItemR43A, *, index: int) -> TwitterXAccountMediaItemR43A:
    if isinstance(item, TwitterXAccountMediaItemR43A):
        return item
    data = dict(item or {})
    return TwitterXAccountMediaItemR43A(media_id=_clean(data.get("media_id") or data.get("source_resource_id") or f"media_{index:06d}"), media_class=_safe_media_class(data.get("media_class") or data.get("type") or data.get("kind") or "media"), source_url=_plain_url(data.get("source_url") or data.get("page_url") or ""), media_url=_plain_url(data.get("media_url") or data.get("url") or data.get("canonical_url") or ""), local_path=_clean(data.get("local_path") or data.get("path") or data.get("file_path") or ""), filename=_safe_filename(data.get("filename") or data.get("display_name") or ""), mime_type=_clean(data.get("mime_type") or data.get("content_type") or ""), width=_safe_int(data.get("width")), height=_safe_int(data.get("height")), duration_seconds=_safe_float(data.get("duration_seconds")), byte_status=_clean(data.get("byte_status") or "metadata_only_review_required"), provenance=_clean(data.get("provenance") or ""), warning=_clean(data.get("warning") or ""))


def _date_folder_for_record(row: TwitterXAccountRecordR43A) -> str:
    return _date_from_text(row.visible_timestamp) or _date_from_text(row.capture_timestamp) or "unknown_date"


def _date_from_text(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    match = re.search(r"(20\d{2})[-_/](\d{2})[-_/](\d{2})", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    match = re.search(r"(20\d{2})(\d{2})(\d{2})T", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return ""


def _record_folder_name(row: TwitterXAccountRecordR43A) -> str:
    rid = _safe_part(row.record_id, "record")
    if row.record_type == "repost":
        return f"repost_{rid}__original_{_safe_part(row.original_post_id, 'unknown_original')}"
    if row.record_type == "quote":
        return f"quote_{rid}"
    if row.record_type == "reply":
        return f"reply_{rid}"
    return f"post_{rid}"


def _write_post_markdown(path: Path, *, row: TwitterXAccountRecordR43A, handle: str, date_folder: str, capture_dir: Path, record_dir: Path, screenshot_rel: str, copied_media: list[dict[str, Any]]) -> None:
    lines = [f"# Twitter/X {row.record_type.title()} {row.record_id}", "", f"- Account capture: `{handle}`", f"- Record type: `{row.record_type}`", f"- Author: `{row.author_handle or 'unknown'}` {row.author_display_name or ''}".rstrip(), f"- Visible timestamp: `{row.visible_timestamp or ''}`", f"- Date folder: `{date_folder}`", f"- Source URL: `{_plain_url(row.source_url)}`", f"- Static screenshot: [{Path(screenshot_rel).name}]({_quote_md_path(_rel(record_dir, capture_dir / screenshot_rel))})", "- Media folder: [media](media/)", "", "## Visible text", "", row.visible_text or "(No visible text captured.)", "", "## Media"]
    if copied_media:
        for item in copied_media:
            local = _rel(record_dir, capture_dir / str(item.get("local_export_path") or ""))
            lines.append(f"- `{item.get('media_class')}` `{item.get('media_id')}`: [{Path(local).name}]({_quote_md_path(local)})")
    else:
        lines.append("- No media item recorded for this post/repost.")
    if row.review_strings:
        lines.extend(["", "## Review strings"])
        for text in row.review_strings:
            lines.append(f"- {text}")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_account_record_markdown(path: Path, *, manifest: Mapping[str, Any], timeline_rows: list[Mapping[str, Any]], media_index: list[Mapping[str, Any]]) -> None:
    by_date: dict[str, list[Mapping[str, Any]]] = {}
    for row in timeline_rows:
        by_date.setdefault(str(row.get("visible_date_folder") or "unknown_date"), []).append(row)
    lines = [f"# Twitter/X Account Media Ledger: @{manifest.get('account_handle')}", "", f"- Marker: `{R43A_MARKER}`", f"- Status: `{manifest.get('status')}`", f"- Capture timestamp: `{manifest.get('capture_timestamp')}`", f"- Total observed records: `{manifest.get('record_count')}`", f"- Media-bearing records/media items: `{manifest.get('media_count')}`", f"- Static screenshots copied: `{manifest.get('screenshot_count')}`", "- Media index: [media_index.json](media_index.json)", "- Timeline NDJSON: [account_timeline.ndjson](account_timeline.ndjson)", "- Progress events: [progress_events.ndjson](progress_events.ndjson)", "- Review strings: [review_strings.txt](review_strings.txt)", "", "## Date folders"]
    for date_folder in manifest.get("date_folders") or []:
        lines.append(f"- [{date_folder}](dates/{date_folder}/)")
    lines.append("")
    for date_folder in manifest.get("date_folders") or []:
        lines.extend([f"## {date_folder}", ""])
        for row in by_date.get(date_folder, []):
            folder = str(row.get("record_folder") or "")
            post_md = str(row.get("post_markdown") or "")
            media_folder = str(row.get("media_folder") or "")
            screenshot = str(row.get("static_screenshot") or "")
            label = f"{row.get('record_type')} {row.get('record_id')}"
            lines.append(f"- [{label}]({post_md})")
            lines.append(f"  - Folder: [{folder}]({folder}/)")
            lines.append(f"  - Static screenshot: [{Path(screenshot).name}]({screenshot})")
            lines.append(f"  - Media folder: [{media_folder}]({media_folder}/)")
            lines.append(f"  - Source URL: `{_plain_url(row.get('source_url'))}`")
        lines.append("")
    lines.extend(["## Media index summary", ""])
    for item in media_index:
        lines.append(f"- `{item.get('media_class')}` for `{item.get('record_id')}`: [{Path(str(item.get('local_export_path') or '')).name}]({item.get('local_export_path')}) in [{item.get('record_folder')}]({item.get('record_folder')}/)")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _review_lines_for_row(row: TwitterXAccountRecordR43A, *, date_folder: str, record_dir: str) -> list[str]:
    lines = [f"[{date_folder}] {row.record_type} {row.record_id} {record_dir}: {_clean(text)}" for text in row.review_strings or () if _clean(text)]
    if not lines and row.visible_text:
        lines.append(f"[{date_folder}] {row.record_type} {row.record_id} {record_dir}: {row.visible_text}")
    return lines


def _copy_receipt_file(source: str, target_stem: Path, *, default_suffix: str) -> tuple[Path, bool]:
    src = Path(source)
    if src.is_file():
        target = target_stem.with_suffix(src.suffix or default_suffix)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        return target, True
    receipt = target_stem.with_suffix(".missing.txt")
    receipt.write_text(f"Referenced file was not available locally: {source}\n", encoding="utf-8")
    return receipt, False


def _copy_or_url_receipt(local_path: str, target: Path, item: TwitterXAccountMediaItemR43A) -> tuple[Path, bool]:
    target.parent.mkdir(parents=True, exist_ok=True)
    if _clean(local_path) and Path(local_path).is_file():
        if not target.suffix:
            target = target.with_suffix(_extension_for_item(item))
        shutil.copy2(local_path, target)
        return target, True
    receipt = target.with_suffix(target.suffix + ".url.txt" if target.suffix else ".url.txt")
    receipt.write_text("Remote/media candidate receipt only. R43A did not download remote media.\n" + f"media_id: {item.media_id}\nmedia_class: {item.media_class}\nmedia_url: {_plain_url(item.media_url)}\nsource_url: {_plain_url(item.source_url)}\nbyte_status: {item.byte_status}\nwarning: {item.warning}\n", encoding="utf-8")
    return receipt, False


def _media_target_dir(item: TwitterXAccountMediaItemR43A, *, image_dir: Path, video_dir: Path, manifest_dir: Path, segment_dir: Path) -> Path:
    cls = _safe_media_class(item.media_class)
    ext = _extension_for_item(item).lower()
    if cls == "image" or ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}:
        return image_dir
    if cls == "segment" or ext in {".ts", ".m4s"}:
        return segment_dir
    if cls == "manifest" or ext in {".m3u8", ".mpd"}:
        return manifest_dir
    return video_dir


def _extension_for_item(item: TwitterXAccountMediaItemR43A) -> str:
    for value in (item.filename, item.local_path, item.media_url, item.source_url):
        suffix = Path(_plain_url(value).split("?", 1)[0]).suffix
        if suffix:
            return suffix[:12]
    return {"image": ".jpg", "manifest": ".m3u8", "segment": ".ts"}.get(_safe_media_class(item.media_class), ".bin")


def _filename_from_url(value: Any) -> str:
    return _safe_filename(Path(_plain_url(value).split("?", 1)[0].rstrip("/")).name)


def _safe_media_class(value: Any) -> str:
    text = _clean(value).lower()
    if text in {"image", "photo", "picture"}: return "image"
    if text in {"video", "mp4", "movie"}: return "video"
    if text in {"manifest", "playlist", "m3u8", "mpd"}: return "manifest"
    if text in {"segment", "chunk", "ts", "m4s"}: return "segment"
    return "media"


def _safe_record_type(value: Any) -> str:
    text = _clean(value).lower()
    if text in {"post", "tweet", "status"}: return "post"
    if text in {"repost", "retweet", "rt"}: return "repost"
    if text in {"quote", "quote_post", "quote_tweet"}: return "quote"
    if text == "reply": return "reply"
    return "post"


def _safe_handle(value: Any) -> str:
    text = re.sub(r"[^a-z0-9_]+", "_", _clean(value).lstrip("@").lower()).strip("_")
    return text[:80] or "unknown_account"


def _safe_part(value: Any, fallback: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", _clean(value)).strip("._-")
    return text[:120] or fallback


def _safe_filename(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9_. -]+", "_", _clean(value)).strip(" ._-")
    return text[:140] or "media.bin"


def _safe_ts(value: Any) -> str:
    text = re.sub(r"[^0-9TZ]", "", _clean(value).replace(":", "").replace("-", "").replace("_", "").upper())
    if re.match(r"^20\d{6}T\d{6}Z$", text): return text
    if re.match(r"^20\d{6}$", text): return text + "T000000Z"
    return ""


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _plain_url(value: Any) -> str:
    text = _clean(value).replace("\\_", "_").replace("\\&", "&").replace("\\/", "/")
    normalized = text.replace("]\\(", "](").replace("\\)", ")")
    match = re.search(r"\]\((https?://[^)\s]+)\)", normalized)
    return (match.group(1) if match else normalized).strip()


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)): return value
    if isinstance(value, Path): return value.as_posix()
    if isinstance(value, Mapping): return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, tuple): return [_to_jsonable(v) for v in value]
    if isinstance(value, list): return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict"):
        try: return _to_jsonable(value.to_dict())
        except Exception: pass
    if is_dataclass(value): return _to_jsonable(asdict(value))
    return _clean(value)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(data), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    data = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(_to_jsonable(row), ensure_ascii=False, sort_keys=True) for row in data) + ("\n" if data else ""), encoding="utf-8")


def _read_json(path: Path, default: Any) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default


def _rel(base: Path, target: Path) -> str:
    try: return target.resolve().relative_to(base.resolve()).as_posix()
    except Exception: return target.as_posix()


def _quote_md_path(value: str) -> str:
    return value.replace(" ", "%20")


def _first_non_empty(values: Iterable[str]) -> str:
    for value in values:
        if _clean(value): return _clean(value)
    return ""


def _sort_dates(values: Iterable[str]) -> list[str]:
    return sorted(values, key=lambda v: (v == "unknown_date", v))


def _safe_int(value: Any) -> int:
    try: return int(value or 0)
    except Exception: return 0


def _safe_float(value: Any) -> float:
    try: return float(value or 0.0)
    except Exception: return 0.0


def _check(name: str, condition: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _scrub_markdown_machine_urls(value: Any) -> Any:
    if isinstance(value, Mapping): return {str(key): _scrub_markdown_machine_urls(item) for key, item in value.items()}
    if isinstance(value, tuple): return tuple(_scrub_markdown_machine_urls(item) for item in value)
    if isinstance(value, list): return [_scrub_markdown_machine_urls(item) for item in value]
    if isinstance(value, str) and ("http://" in value or "https://" in value): return _plain_url(value)
    return value


def _machine_urls_are_plain(value: Any) -> bool:
    blob = json.dumps(_scrub_markdown_machine_urls(_to_jsonable(value)), ensure_ascii=False, sort_keys=True)
    return "](" not in blob and "]\\(" not in blob and '"[http' not in blob


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default=R43A_REPORT_ROOT)
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    print(report.marker)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
