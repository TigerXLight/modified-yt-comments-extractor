from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

R43U_MARKER = "YTCE_R43U_UNIVERSAL_SOCIAL_ACCOUNT_LEDGER_CONTRACT_BASELINE"
R43U_PASS_STATUS = "PASS_R43U_UNIVERSAL_SOCIAL_ACCOUNT_LEDGER_CONTRACT_BASELINE"
R43U_BLOCKED_STATUS = "BLOCKED_R43U_UNIVERSAL_SOCIAL_ACCOUNT_LEDGER_CONTRACT_BASELINE"
R43U_SCHEMA_VERSION = "universal_social_account_ledger_contract.r43u.v1"
R43U_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43u_universal_social_account_ledger_contract_baseline"
R43U_MODE_ID = "universal_social_account_ledger_contract_baseline"

UNIVERSAL_SOCIAL_LEDGER_FILES_R43U = (
    "universal_account_ledger_contract.json",
    "manifest.json",
    "account_record.md",
    "account_timeline.ndjson",
    "media_index.json",
    "progress_events.ndjson",
    "review_strings.txt",
)

UNIVERSAL_SOCIAL_MEDIA_CLASSES_R43U = (
    "image",
    "video",
    "manifest",
    "segment",
    "audio",
    "document",
    "external",
    "other",
)

UNIVERSAL_SOCIAL_RECORD_TYPES_R43U = (
    "post",
    "repost_or_reshare",
    "quote",
    "reply",
    "thread_context",
)


@dataclass(frozen=True)
class UniversalSocialMediaItemR43U:
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
    bound_to_record_id: str = ""
    bound_to_source_url: str = ""
    binding_status: str = ""
    binding_reason: str = ""
    source_observation_kind: str = ""
    source_observation_marker: str = ""
    source_observation_path: str = ""
    metadata_only_remote_media_not_downloaded: bool = True
    playlist_manifest_url: str = ""
    platform_specific: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class UniversalSocialRecordR43U:
    platform_id: str
    account_handle: str
    record_id: str
    record_type: str
    source_url: str
    visible_text: str = ""
    visible_timestamp: str = ""
    capture_timestamp: str = ""
    author_handle: str = ""
    author_display_name: str = ""
    original_record_id: str = ""
    reshared_by_handle: str = ""
    reshare_context: Mapping[str, Any] = field(default_factory=dict)
    static_screenshot_path: str = ""
    media_items: tuple[UniversalSocialMediaItemR43U, ...] = ()
    review_strings: tuple[str, ...] = ()
    observed_order: int = 0
    platform_specific: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["media_items"] = [item.to_dict() if hasattr(item, "to_dict") else _to_jsonable(item) for item in self.media_items]
        data["reshare_context"] = _to_jsonable(dict(self.reshare_context or {}))
        data["platform_specific"] = _to_jsonable(dict(self.platform_specific or {}))
        return _to_jsonable(data)


@dataclass(frozen=True)
class UniversalSocialAccountLedgerWriteResultR43U:
    marker: str
    schema_version: str
    status: str
    platform_id: str
    account_handle: str
    capture_timestamp: str
    output_root: str
    account_capture_dir: str
    contract_path: str
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
        return self.status == R43U_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43UReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    universal_contract: Mapping[str, Any]
    twitter_x_fixture_result: Mapping[str, Any]
    bluesky_fixture_result: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R43U_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [dict(check) for check in self.checks],
            "generated_at": self.generated_at,
            "marker": self.marker,
            "schema_version": self.schema_version,
            "side_effect_flags": dict(self.side_effect_flags),
            "status": self.status,
            "universal_contract": _to_jsonable(self.universal_contract),
            "twitter_x_fixture_result": _to_jsonable(self.twitter_x_fixture_result),
            "bluesky_fixture_result": _to_jsonable(self.bluesky_fixture_result),
        }


class UniversalSocialAccountLedgerWriterR43U:
    """Platform-neutral social account ledger writer.

    R43U freezes the R43T/R43A folder and receipt method as a reusable universal
    contract before Bluesky is added. It writes account/date/post/media/screenshot
    evidence ledgers from already-normalized visible records. It does not start a
    browser, scrape hidden APIs, read cookies/tokens, bypass challenges, or download
    remote media. Platform adapters only normalize their native fields into this
    contract and may put platform-only values under platform_specific.
    """

    def __init__(self, output_root: str | Path = R43U_DEFAULT_OUTPUT_ROOT) -> None:
        self.output_root = Path(output_root)

    def write(
        self,
        records: Iterable[Mapping[str, Any] | UniversalSocialRecordR43U],
        *,
        platform_id: str = "",
        account_handle: str = "",
        capture_timestamp: str = "",
    ) -> UniversalSocialAccountLedgerWriteResultR43U:
        return write_universal_social_account_ledger_r43u(
            records,
            output_root=self.output_root,
            platform_id=platform_id,
            account_handle=account_handle,
            capture_timestamp=capture_timestamp,
        )


def build_universal_social_account_ledger_writer_r43u(output_root: str | Path = R43U_DEFAULT_OUTPUT_ROOT) -> UniversalSocialAccountLedgerWriterR43U:
    return UniversalSocialAccountLedgerWriterR43U(output_root=output_root)


def build_universal_social_account_ledger_contract_r43u() -> dict[str, Any]:
    return {
        "marker": R43U_MARKER,
        "schema_version": R43U_SCHEMA_VERSION,
        "mode_id": R43U_MODE_ID,
        "baseline_source": "R43T Twitter/X fast media observations to post ledger binding plus R43A account/date/post/media folder writer",
        "twitter_x_output_must_remain_backwards_compatible": True,
        "platform_adapters_must_not_copy_twitter_x_internals": True,
        "method_is_reusable_across_twitter_like_platforms": True,
        "universal_flow": [
            "visible_browser_or_imported_session_capture",
            "platform_adapter_normalizes_visible_records",
            "media_observations_are_bound_to_records_by_safe_identifiers_or_dom_proximity",
            "unbound_account_level_media_candidates_are_preserved_without_fake_binding",
            "universal_account_ledger_writer_materializes_account_date_post_media_receipts",
        ],
        "folder_contract": {
            "account_capture": "source_exports/<platform_id>/<account_handle>/account_capture_<timestamp>",
            "date_folder": "dates/<visible_date_folder>",
            "record_folder": "dates/<date>/post_<record_id> or reshare_<record_id>__original_<original_record_id>",
            "media_folders": ["media/images", "media/videos", "media/manifests", "media/segments"],
            "primary_files": list(UNIVERSAL_SOCIAL_LEDGER_FILES_R43U),
        },
        "record_fields": [
            "platform_id", "account_handle", "record_id", "record_type", "source_url",
            "visible_text", "visible_timestamp", "capture_timestamp", "author_handle",
            "author_display_name", "original_record_id", "reshared_by_handle",
            "static_screenshot_path", "media_items", "review_strings", "observed_order",
            "platform_specific",
        ],
        "media_fields": [
            "media_id", "media_class", "source_url", "media_url", "local_path", "filename",
            "mime_type", "width", "height", "duration_seconds", "byte_status", "provenance",
            "warning", "bound_to_record_id", "bound_to_source_url", "binding_status",
            "binding_reason", "source_observation_kind", "source_observation_marker",
            "source_observation_path", "metadata_only_remote_media_not_downloaded",
            "playlist_manifest_url", "platform_specific",
        ],
        "media_classes": list(UNIVERSAL_SOCIAL_MEDIA_CLASSES_R43U),
        "record_types": list(UNIVERSAL_SOCIAL_RECORD_TYPES_R43U),
        "platform_specific_rule": "Native identifiers such as Bluesky did/at_uri/cid/blob_ref or Twitter/X status_id remain nested under platform_specific, while universal folder/media/receipt fields stay top-level.",
        "bluesky_mapping_baseline": {
            "profile_url": "https://bsky.app/profile/<handle-or-did>",
            "post_url": "https://bsky.app/profile/<handle-or-did>/post/<rkey>",
            "protocol_identity": ["did", "at_uri", "cid", "rkey"],
            "embed_types": ["app.bsky.embed.images", "app.bsky.embed.video", "app.bsky.embed.external", "app.bsky.embed.record", "app.bsky.embed.recordWithMedia"],
            "repo_reference_paths": [
                "atproto/lexicons/app/bsky/feed/post.json",
                "atproto/lexicons/app/bsky/feed/getAuthorFeed.json",
                "atproto/lexicons/app/bsky/feed/getPosts.json",
                "atproto/lexicons/app/bsky/feed/getPostThread.json",
                "atproto/lexicons/app/bsky/embed/images.json",
                "atproto/lexicons/app/bsky/embed/video.json",
                "social-app/src/view/com/posts/PostFeedItem.tsx",
                "social-app/src/components/Post/Embed/index.tsx",
                "social-app/bskyweb/templates/post.html",
            ],
        },
        "side_effect_policy": build_r43u_side_effect_flags(),
    }


def write_universal_social_account_ledger_r43u(
    records: Iterable[Mapping[str, Any] | UniversalSocialRecordR43U],
    *,
    output_root: str | Path = R43U_DEFAULT_OUTPUT_ROOT,
    platform_id: str = "",
    account_handle: str = "",
    capture_timestamp: str = "",
) -> UniversalSocialAccountLedgerWriteResultR43U:
    rows = [_coerce_record(row, index=i) for i, row in enumerate(records or (), start=1)]
    safe_platform = _safe_platform_id(platform_id or _first_non_empty(row.platform_id for row in rows) or "unknown_platform")
    capture_ts = _safe_ts(capture_timestamp) or _first_non_empty(row.capture_timestamp for row in rows) or _now_ts()
    capture_ts = _safe_ts(capture_ts) or _now_ts()
    handle = _safe_handle(account_handle or _first_non_empty(row.account_handle for row in rows) or "unknown_account")
    root = Path(output_root) / "source_exports" / safe_platform / handle
    capture_dir = root / f"account_capture_{capture_ts}"
    if capture_dir.exists():
        shutil.rmtree(capture_dir)
    dates_dir = capture_dir / "dates"
    dates_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    manifest_records: list[dict[str, Any]] = []
    timeline_rows: list[dict[str, Any]] = []
    media_index: list[dict[str, Any]] = []
    progress_events: list[dict[str, Any]] = []
    review_lines: list[str] = []
    date_folders: set[str] = set()
    screenshot_count = 0
    post_folder_count = 0

    sorted_rows = sorted(rows, key=lambda row: (_date_folder_for_record(row), row.observed_order or 0, row.record_id))
    for row in sorted_rows:
        date_folder = _date_folder_for_record(row)
        date_source = _date_source_for_record(row)
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
                    "schema_version": R43U_SCHEMA_VERSION,
                    "marker": R43U_MARKER,
                    "platform_id": safe_platform,
                    "account_handle": handle,
                    "record_id": row.record_id,
                    "record_type": row.record_type,
                    "visible_date_folder": date_folder,
                    "record_folder": _rel(capture_dir, record_dir),
                    "local_export_path": _rel(capture_dir, media_target),
                    "copied_local_bytes": bool(copied),
                    "remote_download_performed_by_r43u": False,
                    "bound_to_record_id": item.bound_to_record_id or row.record_id,
                    "bound_to_source_url": _plain_url(item.bound_to_source_url or row.source_url),
                    "binding_status": item.binding_status or "bound_to_post",
                    "binding_reason": item.binding_reason or "record_media_item",
                    "metadata_only_remote_media_not_downloaded": not bool(copied),
                }
            )
            copied_media.append(media_payload)
            media_index.append(media_payload)

        media_counts = _media_counts(copied_media)
        record_payload = row.to_dict()
        record_payload.update(
            {
                "schema_version": R43U_SCHEMA_VERSION,
                "marker": R43U_MARKER,
                "platform_id": safe_platform,
                "account_handle": handle,
                "capture_timestamp": capture_ts,
                "visible_date_folder": date_folder,
                "date_source": date_source,
                "record_folder": _rel(capture_dir, record_dir),
                "static_screenshot": screenshot_rel,
                "media_folder": _rel(capture_dir, media_dir),
                "media_items": copied_media,
                **media_counts,
                "side_effect_flags": build_r43u_side_effect_flags(),
            }
        )
        _write_json(record_dir / "post.json", record_payload)
        if row.record_type in {"repost", "repost_or_reshare", "reshare"} or row.original_record_id:
            _write_json(record_dir / "reshare_context.json", _to_jsonable(row.reshare_context or {"original_record_id": row.original_record_id, "reshared_by_handle": row.reshared_by_handle}))
        _write_post_markdown(record_dir / "post.md", row=row, platform_id=safe_platform, handle=handle, date_folder=date_folder, capture_dir=capture_dir, record_dir=record_dir, screenshot_rel=screenshot_rel, copied_media=copied_media)

        timeline_row = {
            "schema_version": R43U_SCHEMA_VERSION,
            "marker": R43U_MARKER,
            "platform_id": safe_platform,
            "account_handle": handle,
            "record_id": row.record_id,
            "record_type": row.record_type,
            "source_url": _plain_url(row.source_url),
            "visible_timestamp": row.visible_timestamp,
            "capture_timestamp": row.capture_timestamp or capture_ts,
            "visible_date_folder": date_folder,
            "date_source": date_source,
            "record_folder": _rel(capture_dir, record_dir),
            "post_markdown": _rel(capture_dir, record_dir / "post.md"),
            "post_json": _rel(capture_dir, record_dir / "post.json"),
            "static_screenshot": screenshot_rel,
            "media_folder": _rel(capture_dir, media_dir),
            "media_count": len(row.media_items or ()),
            **media_counts,
            "review_string_count": len(row.review_strings or ()),
            "platform_specific": _to_jsonable(dict(row.platform_specific or {})),
        }
        timeline_rows.append(timeline_row)
        manifest_records.append(timeline_row)
        review_lines.extend(_review_lines_for_row(row, date_folder=date_folder, record_dir=_rel(capture_dir, record_dir)))
        progress_events.append(
            {
                "event": "universal_record_folder_written",
                "platform_id": safe_platform,
                "record_id": row.record_id,
                "record_type": row.record_type,
                "visible_date_folder": date_folder,
                "date_source": date_source,
                "record_folder": _rel(capture_dir, record_dir),
                "media_count": len(row.media_items or ()),
                **media_counts,
                "remote_download_performed_by_r43u": False,
            }
        )
        post_folder_count += 1

    date_folder_list = tuple(_sort_dates(date_folders))
    contract = build_universal_social_account_ledger_contract_r43u()
    manifest = {
        "schema_version": R43U_SCHEMA_VERSION,
        "marker": R43U_MARKER,
        "status": R43U_PASS_STATUS,
        "platform_id": safe_platform,
        "account_handle": handle,
        "capture_timestamp": capture_ts,
        "account_capture_dir": str(capture_dir),
        "account_record_path": str(capture_dir / "account_record.md"),
        "record_count": len(rows),
        "media_count": len(media_index),
        "screenshot_count": screenshot_count,
        "date_folders": list(date_folder_list),
        "records": manifest_records,
        "side_effect_flags": build_r43u_side_effect_flags(),
        "folder_contract": contract.get("folder_contract", {}),
        "warnings": warnings,
    }
    _write_json(capture_dir / "universal_account_ledger_contract.json", contract)
    _write_json(capture_dir / "manifest.json", manifest)
    _write_json(capture_dir / "media_index.json", media_index)
    _write_jsonl(capture_dir / "account_timeline.ndjson", timeline_rows)
    _write_jsonl(capture_dir / "progress_events.ndjson", progress_events)
    (capture_dir / "review_strings.txt").write_text("\n".join(review_lines).rstrip() + ("\n" if review_lines else ""), encoding="utf-8")
    _write_account_record_markdown(capture_dir / "account_record.md", manifest=manifest, timeline_rows=timeline_rows, media_index=media_index)

    return UniversalSocialAccountLedgerWriteResultR43U(
        marker=R43U_MARKER,
        schema_version=R43U_SCHEMA_VERSION,
        status=R43U_PASS_STATUS,
        platform_id=safe_platform,
        account_handle=handle,
        capture_timestamp=capture_ts,
        output_root=str(output_root),
        account_capture_dir=str(capture_dir),
        contract_path=str(capture_dir / "universal_account_ledger_contract.json"),
        account_record_path=str(capture_dir / "account_record.md"),
        manifest_path=str(capture_dir / "manifest.json"),
        account_timeline_path=str(capture_dir / "account_timeline.ndjson"),
        media_index_path=str(capture_dir / "media_index.json"),
        progress_events_path=str(capture_dir / "progress_events.ndjson"),
        review_strings_path=str(capture_dir / "review_strings.txt"),
        record_count=len(rows),
        media_count=len(media_index),
        screenshot_count=screenshot_count,
        date_folders=date_folder_list,
        post_folder_count=post_folder_count,
        side_effect_flags=build_r43u_side_effect_flags(),
        warnings=tuple(warnings),
    )


def build_r43u_side_effect_flags() -> dict[str, bool]:
    return {
        "r43u_universal_social_account_ledger_written": True,
        "twitter_x_baseline_preserved_not_replaced": True,
        "remote_media_download_performed_by_r43u": False,
        "network_actions_performed": False,
        "browser_session_started": False,
        "webview2_session_started_by_r43u": False,
        "hidden_platform_api_scraping_performed": False,
        "login_automation_performed": False,
        "cookie_or_token_extraction_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "paywall_or_access_control_bypass_performed": False,
        "review_window_dependency_invoked": False,
        "source_role_checks_performed": False,
        "webview2_internals_copied": False,
        "youtube_capture_engine_changed": False,
    }


def build_fake_twitter_x_fixture_records_r43u(fixture_root: str | Path) -> tuple[UniversalSocialRecordR43U, ...]:
    root = Path(fixture_root)
    root.mkdir(parents=True, exist_ok=True)
    screenshot = root / "twitter_x_static.png"
    image = root / "twitter_x_image.jpg"
    screenshot.write_bytes(b"R43U_TWITTER_X_SCREENSHOT\n")
    image.write_bytes(b"R43U_TWITTER_X_IMAGE\n")
    return (
        UniversalSocialRecordR43U(
            platform_id="twitter_x",
            account_handle="example",
            author_handle="example",
            author_display_name="Example Account",
            record_id="1111111111111111111",
            record_type="post",
            source_url="https://x.com/example/status/1111111111111111111",
            visible_text="Twitter/X baseline fixture for the universal ledger contract.",
            visible_timestamp="2026-09-18T05:00:00Z",
            capture_timestamp="20260918T050000Z",
            static_screenshot_path=str(screenshot),
            media_items=(
                UniversalSocialMediaItemR43U(
                    media_id="twitter_x_img_1",
                    media_class="image",
                    media_url="https://pbs.twimg.com/media/r43u_fixture.jpg?format=jpg&name=large",
                    local_path=str(image),
                    filename="r43u_twitter_x_fixture.jpg",
                    mime_type="image/jpeg",
                    provenance="R43U fake Twitter/X fixture from R43T/R43A baseline shape",
                    binding_status="bound_to_post",
                    binding_reason="fixture_status_id_match",
                    platform_specific={"twitter_x": {"status_id": "1111111111111111111"}},
                    metadata_only_remote_media_not_downloaded=False,
                ),
            ),
            review_strings=("R43U Twitter/X fixture keeps the account/date/post/media ledger shape.",),
            observed_order=1,
            platform_specific={"twitter_x": {"status_id": "1111111111111111111", "canonical_status_url": "https://x.com/example/status/1111111111111111111"}},
        ),
    )


def build_fake_bluesky_fixture_records_r43u(fixture_root: str | Path) -> tuple[UniversalSocialRecordR43U, ...]:
    root = Path(fixture_root)
    root.mkdir(parents=True, exist_ok=True)
    screenshot = root / "bluesky_static.png"
    image = root / "bluesky_image.jpg"
    screenshot.write_bytes(b"R43U_BLUESKY_SCREENSHOT\n")
    image.write_bytes(b"R43U_BLUESKY_IMAGE\n")
    did = "did:plc:exampleblue1234567890"
    rkey = "3lrtestfixture"
    at_uri = f"at://{did}/app.bsky.feed.post/{rkey}"
    return (
        UniversalSocialRecordR43U(
            platform_id="bluesky",
            account_handle="example.bsky.social",
            author_handle="example.bsky.social",
            author_display_name="Example Bluesky Account",
            record_id=rkey,
            record_type="post",
            source_url=f"https://bsky.app/profile/example.bsky.social/post/{rkey}",
            visible_text="Bluesky fixture post using the same universal ledger contract.",
            visible_timestamp="2026-09-18T05:05:00Z",
            capture_timestamp="20260918T050500Z",
            static_screenshot_path=str(screenshot),
            media_items=(
                UniversalSocialMediaItemR43U(
                    media_id="bluesky_blob_1",
                    media_class="image",
                    media_url="https://cdn.bsky.app/img/feed_fullsize/plain/did:plc:exampleblue1234567890/bafkreiexample@jpeg",
                    local_path=str(image),
                    filename="bluesky_fixture_image.jpg",
                    mime_type="image/jpeg",
                    provenance="R43U fake Bluesky fixture mapped from app.bsky.embed.images shape",
                    binding_status="bound_to_post",
                    binding_reason="fixture_at_uri_record_match",
                    platform_specific={"bluesky": {"did": did, "at_uri": at_uri, "cid": "bafyreiexamplepostcid", "blob_ref": "bafkreiexample", "embed_type": "app.bsky.embed.images"}},
                    metadata_only_remote_media_not_downloaded=False,
                ),
                UniversalSocialMediaItemR43U(
                    media_id="bluesky_external_1",
                    media_class="external",
                    media_url="https://example.com/external-card",
                    filename="external-card.url",
                    provenance="R43U fake Bluesky fixture mapped from app.bsky.embed.external shape",
                    binding_status="bound_to_post",
                    binding_reason="fixture_dom_proximity_external_embed",
                    platform_specific={"bluesky": {"did": did, "at_uri": at_uri, "cid": "bafyreiexamplepostcid", "embed_type": "app.bsky.embed.external"}},
                    metadata_only_remote_media_not_downloaded=True,
                    warning="external embed receipt only; R43U did not download remote media",
                ),
            ),
            review_strings=("R43U Bluesky fixture proves platform_specific nesting and shared ledger folders.",),
            observed_order=1,
            platform_specific={"bluesky": {"did": did, "at_uri": at_uri, "cid": "bafyreiexamplepostcid", "rkey": rkey, "app_bsky_url": f"https://bsky.app/profile/example.bsky.social/post/{rkey}", "embed_type": "app.bsky.embed.images"}},
        ),
    )


def build_report(output_root: str | Path = R43U_DEFAULT_OUTPUT_ROOT) -> R43UReport:
    root = Path(output_root)
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    fixture_root = root / "fixture_files"
    twitter_result = write_universal_social_account_ledger_r43u(
        build_fake_twitter_x_fixture_records_r43u(fixture_root / "twitter_x"),
        output_root=root,
        platform_id="twitter_x",
        account_handle="example",
        capture_timestamp="20260918T050000Z",
    )
    bluesky_result = write_universal_social_account_ledger_r43u(
        build_fake_bluesky_fixture_records_r43u(fixture_root / "bluesky"),
        output_root=root,
        platform_id="bluesky",
        account_handle="example.bsky.social",
        capture_timestamp="20260918T050500Z",
    )
    contract = build_universal_social_account_ledger_contract_r43u()
    twitter_manifest = _read_json(Path(twitter_result.manifest_path), {})
    bluesky_manifest = _read_json(Path(bluesky_result.manifest_path), {})
    bluesky_post_json_paths = list(Path(bluesky_result.account_capture_dir).glob("dates/*/post_*/post.json"))
    bluesky_post = _read_json(bluesky_post_json_paths[0], {}) if bluesky_post_json_paths else {}
    bluesky_media_index = _read_json(Path(bluesky_result.media_index_path), [])
    checks = (
        _check("contract_freezes_r43t_method_not_twitter_internals", contract.get("method_is_reusable_across_twitter_like_platforms") is True and contract.get("platform_adapters_must_not_copy_twitter_x_internals") is True),
        _check("folder_contract_is_platform_neutral", contract.get("folder_contract", {}).get("account_capture") == "source_exports/<platform_id>/<account_handle>/account_capture_<timestamp>"),
        _check("twitter_x_fixture_writes_same_account_date_post_media_shape", twitter_result.passed and Path(twitter_result.account_capture_dir, "dates", "2026-09-18", "post_1111111111111111111", "post.md").is_file()),
        _check("bluesky_fixture_writes_same_account_date_post_media_shape", bluesky_result.passed and bool(bluesky_post_json_paths) and Path(bluesky_result.account_record_path).is_file()),
        _check("bluesky_identity_stays_in_platform_specific", bool((bluesky_post.get("platform_specific") or {}).get("bluesky", {}).get("at_uri")) and "did" in (bluesky_post.get("platform_specific") or {}).get("bluesky", {})),
        _check("bluesky_embed_media_stays_in_universal_media_index", len(bluesky_media_index) == 2 and all((row.get("platform_specific") or {}).get("bluesky") for row in bluesky_media_index)),
        _check("remote_media_downloads_are_not_performed", twitter_result.side_effect_flags.get("remote_media_download_performed_by_r43u") is False and bluesky_result.side_effect_flags.get("remote_media_download_performed_by_r43u") is False),
        _check("primary_ledger_files_written_for_both_platforms", all(Path(twitter_result.account_capture_dir, name).is_file() for name in UNIVERSAL_SOCIAL_LEDGER_FILES_R43U) and all(Path(bluesky_result.account_capture_dir, name).is_file() for name in UNIVERSAL_SOCIAL_LEDGER_FILES_R43U)),
        _check("manifest_records_include_platform_id", twitter_manifest.get("platform_id") == "twitter_x" and bluesky_manifest.get("platform_id") == "bluesky"),
        _check("plain_machine_urls", _machine_urls_are_plain({"contract": contract, "twitter": twitter_result.to_dict(), "bluesky": bluesky_result.to_dict(), "bluesky_post": bluesky_post})),
    )
    status = R43U_PASS_STATUS if all(check.get("status") == "pass" for check in checks) else R43U_BLOCKED_STATUS
    report = R43UReport(
        marker=R43U_MARKER,
        schema_version=R43U_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=checks,
        universal_contract=contract,
        twitter_x_fixture_result=twitter_result.to_dict(),
        bluesky_fixture_result=bluesky_result.to_dict(),
        side_effect_flags=build_r43u_side_effect_flags(),
    )
    _write_json(root / "R43U_UNIVERSAL_SOCIAL_ACCOUNT_LEDGER_CONTRACT_BASELINE_REPORT.json", report.to_dict())
    _write_text(root / "R43U_UNIVERSAL_SOCIAL_ACCOUNT_LEDGER_CONTRACT_BASELINE_REPORT.md", _report_md(report))
    return report


def _report_md(report: R43UReport) -> str:
    lines = [
        "# R43U Universal Social Account Ledger Contract Baseline",
        "",
        f"Status: `{report.status}`",
        f"Marker: `{report.marker}`",
        "",
        "## Purpose",
        "",
        "Freeze the R43T/R43A Twitter/X account-ledger method as a platform-neutral contract before adding Bluesky.",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.append(f"- {check.get('status')}: {check.get('name')}")
    lines.extend([
        "",
        "## Fixture outputs",
        "",
        f"- Twitter/X: `{report.twitter_x_fixture_result.get('account_capture_dir')}`",
        f"- Bluesky: `{report.bluesky_fixture_result.get('account_capture_dir')}`",
    ])
    return "\n".join(lines).rstrip() + "\n"


def _coerce_record(value: Mapping[str, Any] | UniversalSocialRecordR43U, *, index: int = 0) -> UniversalSocialRecordR43U:
    if isinstance(value, UniversalSocialRecordR43U):
        if value.observed_order:
            return value
        data = value.to_dict()
    elif is_dataclass(value):
        data = asdict(value)
    else:
        data = dict(value or {})
    platform_id = _safe_platform_id(data.get("platform_id") or data.get("platform") or "")
    record_id = _safe_record_id(data.get("record_id") or data.get("post_id") or data.get("status_id") or data.get("rkey") or data.get("uri") or f"record_{index:04d}")
    return UniversalSocialRecordR43U(
        platform_id=platform_id,
        account_handle=_safe_handle(data.get("account_handle") or data.get("handle") or data.get("profile_handle") or ""),
        record_id=record_id,
        record_type=_safe_record_type(data.get("record_type") or data.get("type") or "post"),
        source_url=_plain_url(data.get("source_url") or data.get("canonical_post_url") or data.get("url") or ""),
        visible_text=_clean(data.get("visible_text") or data.get("text") or ""),
        visible_timestamp=_clean(data.get("visible_timestamp") or data.get("indexed_at") or data.get("created_at") or ""),
        capture_timestamp=_safe_ts(data.get("capture_timestamp") or ""),
        author_handle=_safe_handle(data.get("author_handle") or data.get("author") or ""),
        author_display_name=_clean(data.get("author_display_name") or data.get("display_name") or ""),
        original_record_id=_safe_record_id(data.get("original_record_id") or data.get("original_post_id") or ""),
        reshared_by_handle=_safe_handle(data.get("reshared_by_handle") or data.get("reposted_by_handle") or ""),
        reshare_context=_to_jsonable(data.get("reshare_context") or data.get("repost_context") or {}),
        static_screenshot_path=_clean(data.get("static_screenshot_path") or ""),
        media_items=tuple(_coerce_media_item(item) for item in data.get("media_items") or ()),
        review_strings=tuple(_clean(x) for x in data.get("review_strings") or () if _clean(x)),
        observed_order=_safe_int(data.get("observed_order"), index),
        platform_specific=_to_jsonable(data.get("platform_specific") or {}),
    )


def _coerce_media_item(value: Mapping[str, Any] | UniversalSocialMediaItemR43U) -> UniversalSocialMediaItemR43U:
    if isinstance(value, UniversalSocialMediaItemR43U):
        return value
    if is_dataclass(value):
        data = asdict(value)
    else:
        data = dict(value or {})
    media_url = _plain_url(data.get("media_url") or data.get("url") or data.get("fullsize") or data.get("thumb") or "")
    return UniversalSocialMediaItemR43U(
        media_id=_safe_part(data.get("media_id") or data.get("blob_ref") or media_url or "media", "media"),
        media_class=_safe_media_class(data.get("media_class") or data.get("kind") or data.get("type") or "other"),
        source_url=_plain_url(data.get("source_url") or ""),
        media_url=media_url,
        local_path=_clean(data.get("local_path") or data.get("local_session_path") or ""),
        filename=_safe_filename(data.get("filename") or ""),
        mime_type=_clean(data.get("mime_type") or data.get("content_type") or ""),
        width=_safe_int(data.get("width"), 0),
        height=_safe_int(data.get("height"), 0),
        duration_seconds=_safe_float(data.get("duration_seconds"), 0.0),
        byte_status=_clean(data.get("byte_status") or "metadata_only_review_required"),
        provenance=_clean(data.get("provenance") or ""),
        warning=_clean(data.get("warning") or ""),
        bound_to_record_id=_safe_record_id(data.get("bound_to_record_id") or ""),
        bound_to_source_url=_plain_url(data.get("bound_to_source_url") or ""),
        binding_status=_clean(data.get("binding_status") or ""),
        binding_reason=_clean(data.get("binding_reason") or ""),
        source_observation_kind=_clean(data.get("source_observation_kind") or ""),
        source_observation_marker=_clean(data.get("source_observation_marker") or ""),
        source_observation_path=_clean(data.get("source_observation_path") or ""),
        metadata_only_remote_media_not_downloaded=bool(data.get("metadata_only_remote_media_not_downloaded", True)),
        playlist_manifest_url=_plain_url(data.get("playlist_manifest_url") or data.get("manifest_url") or ""),
        platform_specific=_to_jsonable(data.get("platform_specific") or {}),
    )


def _write_post_markdown(path: Path, *, row: UniversalSocialRecordR43U, platform_id: str, handle: str, date_folder: str, capture_dir: Path, record_dir: Path, screenshot_rel: str, copied_media: list[dict[str, Any]]) -> None:
    counts = _media_counts(copied_media)
    lines = [
        f"# {platform_id} {row.record_type} {row.record_id}",
        "",
        f"- Account capture: `{handle}`",
        f"- Platform: `{platform_id}`",
        f"- Record type: `{row.record_type}`",
        f"- Author: `{row.author_handle or 'unknown'}` {row.author_display_name or ''}".rstrip(),
        f"- Visible timestamp: `{row.visible_timestamp or ''}`",
        f"- Date folder: `{date_folder}`",
        f"- Date source: `{_date_source_for_record(row)}`",
        f"- Source URL: `{_plain_url(row.source_url)}`",
        f"- Static screenshot: [{Path(screenshot_rel).name}]({_quote_md_path(_rel(record_dir, capture_dir / screenshot_rel))})",
        "- Media folder: [media](media/)",
        f"- Media count: `{counts['media_count']}` images `{counts['image_count']}`, videos `{counts['video_count']}`, manifests `{counts['manifest_count']}`, segments `{counts['segment_count']}`, external `{counts['external_count']}`",
        f"- Session-local media copied: `{counts['session_local_media_count']}`",
        f"- Metadata-only media receipts: `{counts['metadata_only_media_count']}`",
        "",
        "## Visible text",
        "",
        row.visible_text or "(No visible text captured.)",
        "",
        "## Media",
    ]
    if copied_media:
        for item in copied_media:
            local = _rel(record_dir, capture_dir / str(item.get("local_export_path") or ""))
            lines.append(f"- `{item.get('media_class')}` `{item.get('media_id')}`: [{Path(local).name}]({_quote_md_path(local)}) binding `{item.get('binding_status') or 'bound_to_post'}` via `{item.get('binding_reason') or 'record_media_item'}`")
    else:
        lines.append("- No media item recorded for this post/repost.")
    if row.platform_specific:
        lines.extend(["", "## Platform-specific identifiers", "", "```json", json.dumps(_to_jsonable(row.platform_specific), indent=2, sort_keys=True), "```"])
    if row.review_strings:
        lines.extend(["", "## Review strings"])
        for text in row.review_strings:
            lines.append(f"- {text}")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_account_record_markdown(path: Path, *, manifest: Mapping[str, Any], timeline_rows: list[Mapping[str, Any]], media_index: list[Mapping[str, Any]]) -> None:
    by_date: dict[str, list[Mapping[str, Any]]] = {}
    for row in timeline_rows:
        by_date.setdefault(str(row.get("visible_date_folder") or "unknown_date"), []).append(row)
    platform_id = _clean(manifest.get("platform_id"))
    lines = [
        f"# Universal Social Account Ledger: {platform_id} @{manifest.get('account_handle')}",
        "",
        f"- Marker: `{R43U_MARKER}`",
        f"- Status: `{manifest.get('status')}`",
        f"- Platform: `{platform_id}`",
        f"- Capture timestamp: `{manifest.get('capture_timestamp')}`",
        f"- Total observed records: `{manifest.get('record_count')}`",
        f"- Media items: `{manifest.get('media_count')}`",
        f"- Static screenshots copied: `{manifest.get('screenshot_count')}`",
        "- Contract: [universal_account_ledger_contract.json](universal_account_ledger_contract.json)",
        "- Media index: [media_index.json](media_index.json)",
        "- Timeline NDJSON: [account_timeline.ndjson](account_timeline.ndjson)",
        "- Progress events: [progress_events.ndjson](progress_events.ndjson)",
        "- Review strings: [review_strings.txt](review_strings.txt)",
        "",
        "## Date folders",
    ]
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
            lines.append(f"  - Media counts: `{row.get('media_count', 0)}` total, `{row.get('image_count', 0)}` images, `{row.get('video_count', 0)}` videos, `{row.get('manifest_count', 0)}` manifests, `{row.get('segment_count', 0)}` segments, `{row.get('external_count', 0)}` external")
            lines.append(f"  - Local/metadata-only: `{row.get('session_local_media_count', 0)}` local, `{row.get('metadata_only_media_count', 0)}` metadata-only")
            lines.append(f"  - Source URL: `{_plain_url(row.get('source_url'))}`")
        lines.append("")
    lines.extend(["## Media index summary", ""])
    if media_index:
        for item in media_index:
            lines.append(f"- `{item.get('media_class')}` for `{item.get('record_id')}`: [{Path(str(item.get('local_export_path') or '')).name}]({item.get('local_export_path')}) in [{item.get('record_folder')}]({item.get('record_folder')}/)")
    else:
        lines.append("- No media index rows were written.")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _date_folder_for_record(row: UniversalSocialRecordR43U) -> str:
    return _date_from_text(row.visible_timestamp) or _date_from_text(row.capture_timestamp) or "unknown_date"


def _date_source_for_record(row: UniversalSocialRecordR43U) -> str:
    context_source = _clean((row.reshare_context or {}).get("date_source") if isinstance(row.reshare_context, Mapping) else "")
    if context_source:
        return context_source
    for text in row.review_strings or ():
        match = re.search(r"\bdate_source=([A-Za-z0-9_:-]+)", _clean(text))
        if match:
            return match.group(1)
    if _clean(row.visible_timestamp) == "unknown_date":
        return "unknown_date"
    return "visible_timestamp_or_capture_timestamp"


def _date_from_text(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    if text == "unknown_date":
        return "unknown_date"
    match = re.search(r"(20\d{2})[-_/](\d{2})[-_/](\d{2})", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    match = re.search(r"(20\d{2})(\d{2})(\d{2})T", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return ""


def _record_folder_name(row: UniversalSocialRecordR43U) -> str:
    rid = _safe_part(row.record_id, "record")
    rtype = _safe_record_type(row.record_type)
    if rtype in {"repost", "repost_or_reshare", "reshare"}:
        return f"reshare_{rid}__original_{_safe_part(row.original_record_id, 'unknown_original')}"
    if rtype == "quote":
        return f"quote_{rid}"
    if rtype == "reply":
        return f"reply_{rid}"
    if rtype == "thread_context":
        return f"thread_{rid}"
    return f"post_{rid}"


def _media_target_dir(item: UniversalSocialMediaItemR43U, *, image_dir: Path, video_dir: Path, manifest_dir: Path, segment_dir: Path) -> Path:
    cls = _safe_media_class(item.media_class)
    if cls == "image":
        return image_dir
    if cls == "video":
        return video_dir
    if cls == "manifest":
        return manifest_dir
    if cls == "segment":
        return segment_dir
    return image_dir.parent / "other"


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


def _copy_or_url_receipt(local_path: str, target: Path, item: UniversalSocialMediaItemR43U) -> tuple[Path, bool]:
    target.parent.mkdir(parents=True, exist_ok=True)
    if _clean(local_path) and Path(local_path).is_file():
        if not target.suffix:
            target = target.with_suffix(_extension_for_item(item))
        shutil.copy2(local_path, target)
        return target, True
    receipt = target.with_suffix(target.suffix + ".url.txt" if target.suffix else ".url.txt")
    receipt.write_text(
        "Remote/media candidate receipt only. R43U did not download remote media.\n"
        + f"media_id: {item.media_id}\n"
        + f"media_class: {item.media_class}\n"
        + f"media_url: {_plain_url(item.media_url)}\n"
        + f"source_url: {_plain_url(item.source_url)}\n"
        + f"byte_status: {item.byte_status}\n"
        + f"warning: {item.warning}\n",
        encoding="utf-8",
    )
    return receipt, False


def _media_counts(items: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    rows = list(items or ())
    return {
        "media_count": len(rows),
        "image_count": sum(1 for row in rows if _safe_media_class(row.get("media_class")) == "image"),
        "video_count": sum(1 for row in rows if _safe_media_class(row.get("media_class")) == "video"),
        "manifest_count": sum(1 for row in rows if _safe_media_class(row.get("media_class")) == "manifest"),
        "segment_count": sum(1 for row in rows if _safe_media_class(row.get("media_class")) == "segment"),
        "audio_count": sum(1 for row in rows if _safe_media_class(row.get("media_class")) == "audio"),
        "document_count": sum(1 for row in rows if _safe_media_class(row.get("media_class")) == "document"),
        "external_count": sum(1 for row in rows if _safe_media_class(row.get("media_class")) == "external"),
        "other_count": sum(1 for row in rows if _safe_media_class(row.get("media_class")) == "other"),
        "metadata_only_media_count": sum(1 for row in rows if not row.get("copied_local_bytes")),
        "session_local_media_count": sum(1 for row in rows if row.get("copied_local_bytes")),
    }


def _review_lines_for_row(row: UniversalSocialRecordR43U, *, date_folder: str, record_dir: str) -> list[str]:
    lines = [f"[{date_folder}] {row.platform_id} {row.record_type} {row.record_id} {record_dir}: {_clean(text)}" for text in row.review_strings or () if _clean(text)]
    if not lines and row.visible_text:
        lines.append(f"[{date_folder}] {row.platform_id} {row.record_type} {row.record_id} {record_dir}: {row.visible_text}")
    return lines


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(_to_jsonable(row), sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _check(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": detail if not ok else ""}


def _machine_urls_are_plain(payload: Any) -> bool:
    blob = json.dumps(_to_jsonable(payload), sort_keys=True)
    return "](" not in blob and "]\\(" not in blob and '"[http' not in blob


def _plain_url(value: Any) -> str:
    text = _clean(value)
    markdown = re.fullmatch(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", text)
    if markdown:
        return markdown.group(2)
    return text.replace("\\_", "_").replace("\\:", ":")


def _filename_from_url(value: Any) -> str:
    text = _plain_url(value).split("?", 1)[0].rstrip("/")
    name = text.rsplit("/", 1)[-1] if "/" in text else text
    return _safe_filename(name)


def _extension_for_item(item: UniversalSocialMediaItemR43U) -> str:
    cls = _safe_media_class(item.media_class)
    mime = _clean(item.mime_type).lower()
    url = _plain_url(item.media_url).lower().split("?", 1)[0]
    for suffix in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".m3u8", ".ts", ".json", ".html", ".url"):
        if url.endswith(suffix):
            return suffix
    if "jpeg" in mime:
        return ".jpg"
    if "png" in mime:
        return ".png"
    if "webp" in mime:
        return ".webp"
    if "mp4" in mime:
        return ".mp4"
    if "mpegurl" in mime or "m3u8" in mime:
        return ".m3u8"
    if cls == "image":
        return ".jpg"
    if cls == "video":
        return ".mp4"
    if cls == "manifest":
        return ".m3u8"
    if cls == "segment":
        return ".ts"
    if cls == "external":
        return ".url"
    return ".txt"


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except Exception:
        return path.as_posix()


def _quote_md_path(value: str) -> str:
    return value.replace(" ", "%20")


def _safe_platform_id(value: Any) -> str:
    text = _clean(value).lower()
    if text == "twitter":
        text = "twitter_x"
    text = text.replace("x/twitter", "twitter_x").replace("twitter/x", "twitter_x")
    text = re.sub(r"[^a-z0-9_]+", "_", text).strip("_")
    if text in {"x", "twitterx", "twitter_x_com"}:
        return "twitter_x"
    return text or "unknown_platform"


def _safe_handle(value: Any) -> str:
    text = _clean(value).strip().lstrip("@")
    text = re.sub(r"[^A-Za-z0-9_.:-]+", "_", text).strip("._-")
    return text or "unknown_account"


def _safe_record_id(value: Any) -> str:
    text = _clean(value)
    if text.startswith("at://"):
        text = text.rstrip("/").rsplit("/", 1)[-1]
    text = re.sub(r"[^A-Za-z0-9_.:-]+", "_", text).strip("._-")
    return text or "unknown_record"


def _safe_record_type(value: Any) -> str:
    text = re.sub(r"[^a-z0-9_]+", "_", _clean(value).lower()).strip("_")
    if text in {"repost", "reshare", "boost", "share"}:
        return "repost_or_reshare"
    if text in {"post", "quote", "reply", "thread_context"}:
        return text
    return "post"


def _safe_media_class(value: Any) -> str:
    text = re.sub(r"[^a-z0-9_]+", "_", _clean(value).lower()).strip("_")
    if text in {"photo", "thumb", "thumbnail", "gallery"}:
        return "image"
    if text in {"m3u8", "playlist"}:
        return "manifest"
    if text in {"ts", "chunk"}:
        return "segment"
    if text in UNIVERSAL_SOCIAL_MEDIA_CLASSES_R43U:
        return text
    return "other"


def _safe_filename(value: Any) -> str:
    text = _clean(value)
    text = re.sub(r"[<>:\"/\\|?*\x00-\x1F]+", "_", text).strip(" ._")
    return text[:160] if text else "media"


def _safe_part(value: Any, default: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.:-]+", "_", _clean(value)).strip("._-")
    return text or default


def _safe_ts(value: Any) -> str:
    text = _clean(value).replace(":", "").replace("-", "")
    return re.sub(r"[^0-9TZ]", "", text)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return default


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _first_non_empty(values: Iterable[Any]) -> str:
    for value in values:
        text = _clean(value)
        if text:
            return text
    return ""


def _sort_dates(values: Iterable[str]) -> list[str]:
    return sorted(values, key=lambda value: (value == "unknown_date", value))


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


if __name__ == "__main__":
    report = build_report()
    print(R43U_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
