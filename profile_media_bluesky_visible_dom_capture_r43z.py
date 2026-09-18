from __future__ import annotations

import argparse
import base64
import html as html_lib
import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from profile_media_bluesky_visible_account_adapter_r43v import (
    R43V_PASS_STATUS,
    BlueskyVisibleAccountAdapterRequestR43V,
    build_bluesky_visible_account_adapter_r43v,
    build_bluesky_post_url_r43v,
    parse_bluesky_app_url_r43v,
)
from profile_media_universal_social_account_ledger_contract_r43u import R43U_PASS_STATUS

R43Z_MARKER = "YTCE_R43Z_BLUESKY_VISIBLE_DOM_CAPTURE_LANE"
R43Z_PASS_STATUS = "PASS_R43Z_BLUESKY_VISIBLE_DOM_CAPTURE_LANE"
R43Z_BLOCKED_STATUS = "BLOCKED_R43Z_BLUESKY_VISIBLE_DOM_CAPTURE_LANE"
R43Z_SCHEMA_VERSION = "bluesky_visible_dom_capture_lane.r43z.v1"
R43Z_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43z_bluesky_visible_dom_capture_lane"
R43Z_MODE_ID = "bluesky_visible_dom_capture_lane"

_TINY_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="


@dataclass(frozen=True)
class BlueskyVisibleDomCaptureRequestR43Z:
    account_url: str = ""
    account_handle: str = ""
    capture_timestamp: str = ""
    output_root: str = R43Z_DEFAULT_OUTPUT_ROOT
    fixture_mode: bool = False
    explicit_live_mode: bool = False
    run_visible_live: bool = False
    live_mode: bool = False
    visible_dom_html: str = ""
    visible_dom_html_path: str = ""
    static_screenshot_path: str = ""
    observed_media: tuple[Mapping[str, Any], ...] = ()
    include_media: bool = True
    include_static_screenshots: bool = True
    require_screenshot_receipts: bool = True
    max_items: int = 5
    max_scrolls: int = 2

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class BlueskyVisibleDomCaptureResultR43Z:
    marker: str
    schema_version: str
    status: str
    account_handle: str
    account_url: str
    capture_timestamp: str
    output_root: str
    run_dir: str
    request_path: str
    receipt_path: str
    visible_dom_html_path: str = ""
    copied_screenshot_path: str = ""
    visible_dom_posts_path: str = ""
    visible_media_candidates_path: str = ""
    visible_screenshot_receipts_path: str = ""
    adapter_status: str = ""
    adapter_receipt_path: str = ""
    ledger_status: str = ""
    account_capture_dir: str = ""
    account_record_path: str = ""
    manifest_path: str = ""
    account_timeline_path: str = ""
    media_index_path: str = ""
    progress_events_path: str = ""
    review_strings_path: str = ""
    visible_record_count: int = 0
    dom_article_count: int = 0
    media_candidate_count: int = 0
    bound_media_count: int = 0
    unbound_media_count: int = 0
    record_count: int = 0
    media_count: int = 0
    screenshot_count: int = 0
    post_folder_count: int = 0
    date_folders: tuple[str, ...] = ()
    normalized_records: tuple[Mapping[str, Any], ...] = ()
    side_effect_flags: Mapping[str, bool] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R43Z_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43ZReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    sample_result: Mapping[str, Any]
    contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R43Z_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


class BlueskyVisibleDomCaptureLaneR43Z:
    """Visible-DOM evidence importer for Bluesky.

    R43Z is deliberately an evidence ingestion lane, not a browser automation lane.
    It accepts visible page HTML/screenshots captured by a caller, binds nearby media
    URLs to visible Bluesky post cards by DOM proximity, then delegates normalized
    records to the proven R43V -> R43U ledger path. It never reads browser cookies,
    tokens, WebView2 profile storage, cache files, local storage, or remote media bytes.
    """

    def __init__(self, output_root: str | Path = R43Z_DEFAULT_OUTPUT_ROOT) -> None:
        self.output_root = Path(output_root)

    def run_account_export(
        self,
        request: BlueskyVisibleDomCaptureRequestR43Z | Mapping[str, Any] | None = None,
        **overrides: Any,
    ) -> BlueskyVisibleDomCaptureResultR43Z:
        req = coerce_bluesky_visible_dom_capture_request_r43z(request, **overrides)
        return run_bluesky_visible_dom_capture_r43z(req, output_root=self.output_root)


def build_bluesky_visible_dom_capture_r43z(output_root: str | Path = R43Z_DEFAULT_OUTPUT_ROOT) -> BlueskyVisibleDomCaptureLaneR43Z:
    return BlueskyVisibleDomCaptureLaneR43Z(output_root=output_root)


def build_bluesky_visible_dom_capture_contract_r43z() -> dict[str, Any]:
    return {
        "marker": R43Z_MARKER,
        "schema_version": R43Z_SCHEMA_VERSION,
        "mode_id": R43Z_MODE_ID,
        "accepted_inputs": [
            "visible Bluesky profile/post DOM HTML captured by an operator-controlled visible browser",
            "optional visible screenshot file receipts supplied by the caller",
            "optional caller-supplied visible media observations",
            "fixture_mode HTML used only for local validation",
        ],
        "visible_dom_strategy": [
            "extract bsky.app/profile/<handle>/post/<rkey> links from visible post cards",
            "use article/card DOM proximity to bind img/video/source/poster URLs to the nearest post",
            "copy caller-supplied screenshots as receipt files only",
            "emit metadata-only media receipt rows without downloading remote media",
            "feed normalized records through R43V and R43U so the same account/date/post/media ledger is used",
        ],
        "explicit_non_goals": [
            "no browser is started by R43Z",
            "no WebView2 user-data directory is copied or read",
            "no cookies, tokens, cache, local storage, or login database files are read",
            "no login automation, captcha/challenge bypass, hidden platform API scraping, or remote media download is performed",
        ],
        "downstream_adapter": "profile_media_bluesky_visible_account_adapter_r43v",
        "downstream_ledger": "profile_media_universal_social_account_ledger_contract_r43u",
        "repo_reference_paths": [
            "social-app/src/view/com/posts/PostFeedItem.tsx",
            "social-app/src/components/Post/Embed/ImageEmbed.tsx",
            "social-app/src/components/Post/Embed/VideoEmbed/index.web.tsx",
            "social-app/bskyweb/templates/post.html",
            "atproto/lexicons/app/bsky/feed/defs.json",
            "atproto/lexicons/app/bsky/embed/images.json",
            "atproto/lexicons/app/bsky/embed/video.json",
        ],
        "browser_session_started_by_r43z": False,
        "network_requests_performed_by_r43z": False,
        "remote_media_downloads_performed_by_r43z": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "hidden_platform_api_scraping_performed": False,
    }


def run_bluesky_visible_dom_capture_r43z(
    request: BlueskyVisibleDomCaptureRequestR43Z | Mapping[str, Any] | None = None,
    *,
    output_root: str | Path = R43Z_DEFAULT_OUTPUT_ROOT,
) -> BlueskyVisibleDomCaptureResultR43Z:
    req = coerce_bluesky_visible_dom_capture_request_r43z(request)
    root = Path(req.output_root or output_root or R43Z_DEFAULT_OUTPUT_ROOT)
    capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
    account_url = _plain_url(req.account_url)
    parsed_url = parse_bluesky_app_url_r43v(account_url)
    handle = _safe_handle(req.account_handle or parsed_url.get("handle") or "example.bsky.social")
    if not account_url:
        account_url = f"https://bsky.app/profile/{handle}"
    run_dir = root / handle / f"bluesky_visible_dom_capture_{capture_ts}"
    evidence_dir = run_dir / "visible_dom_evidence"
    screenshot_dir = run_dir / "visible_screenshot_receipts"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    request_path = run_dir / "r43z_bluesky_visible_dom_capture_request.json"
    receipt_path = run_dir / "r43z_bluesky_visible_dom_capture_receipt.json"
    visible_posts_path = run_dir / "visible_dom_posts.json"
    visible_media_candidates_path = run_dir / "visible_media_candidates.json"
    visible_screenshot_receipts_path = run_dir / "visible_screenshot_receipts.json"
    _write_json(request_path, req.to_dict())

    warnings: list[str] = []
    html_text = _load_visible_html(req)
    if req.fixture_mode and not html_text:
        html_text = build_fake_bluesky_visible_dom_html_r43z(account_handle=handle)
    html_receipt_path = evidence_dir / "visible_dom.html"
    html_receipt_path.write_text(html_text, encoding="utf-8")

    screenshot_path = _materialize_visible_screenshot(req, screenshot_dir, fixture_mode=req.fixture_mode)
    if req.include_static_screenshots and req.require_screenshot_receipts and not screenshot_path:
        warnings.append("R43Z requires screenshot receipts but no screenshot file was supplied or generated.")

    extracted_records, bound_media, unbound_media = extract_visible_dom_records_r43z(
        html_text,
        account_handle=handle,
        account_url=account_url,
        capture_timestamp=capture_ts,
        html_receipt_path=str(html_receipt_path),
        screenshot_path=str(screenshot_path) if screenshot_path else "",
        observed_media=req.observed_media,
        max_items=req.max_items,
        include_media=req.include_media,
        include_static_screenshots=req.include_static_screenshots,
    )

    _write_json(visible_posts_path, extracted_records)
    _write_json(visible_media_candidates_path, {"bound": bound_media, "unbound": unbound_media})
    _write_json(visible_screenshot_receipts_path, {"copied_screenshot_path": str(screenshot_path) if screenshot_path else "", "record_count": len(extracted_records), "receipt_mode": "copy_supplied_visible_screenshot_only"})

    if not extracted_records:
        warnings.append("No Bluesky visible DOM post cards were extracted.")
        result = _blocked_result(req=req, root=root, run_dir=run_dir, request_path=request_path, receipt_path=receipt_path, handle=handle, account_url=account_url, capture_ts=capture_ts, html_path=html_receipt_path, screenshot_path=screenshot_path, visible_posts_path=visible_posts_path, visible_media_candidates_path=visible_media_candidates_path, visible_screenshot_receipts_path=visible_screenshot_receipts_path, warnings=warnings)
        _write_json(receipt_path, result.to_dict())
        return result

    adapter = build_bluesky_visible_account_adapter_r43v(output_root=run_dir / "r43v_adapter")
    adapter_request = BlueskyVisibleAccountAdapterRequestR43V(
        account_url=account_url,
        account_handle=handle,
        capture_timestamp=capture_ts,
        output_root=str(run_dir / "r43v_adapter"),
        fixture_mode=False,
        initial_records=tuple(extracted_records),
        include_media=req.include_media,
        include_static_screenshots=req.include_static_screenshots,
        require_screenshot_receipts=req.require_screenshot_receipts,
        explicit_live_mode=req.explicit_live_mode,
        run_visible_live=req.run_visible_live,
        live_mode=req.live_mode,
        max_items=req.max_items,
        max_scrolls=req.max_scrolls,
    )
    adapter_result = adapter.run_account_export(adapter_request, initial_records=tuple(extracted_records))
    adapter_payload = adapter_result.to_dict()
    status = R43Z_PASS_STATUS if adapter_result.status == R43V_PASS_STATUS and adapter_result.ledger_status == R43U_PASS_STATUS and adapter_result.record_count > 0 else R43Z_BLOCKED_STATUS
    if adapter_result.status != R43V_PASS_STATUS:
        warnings.append(f"R43V downstream adapter returned {adapter_result.status}.")

    result = BlueskyVisibleDomCaptureResultR43Z(
        marker=R43Z_MARKER,
        schema_version=R43Z_SCHEMA_VERSION,
        status=status,
        account_handle=handle,
        account_url=account_url,
        capture_timestamp=capture_ts,
        output_root=str(root),
        run_dir=str(run_dir),
        request_path=str(request_path),
        receipt_path=str(receipt_path),
        visible_dom_html_path=str(html_receipt_path),
        copied_screenshot_path=str(screenshot_path) if screenshot_path else "",
        visible_dom_posts_path=str(visible_posts_path),
        visible_media_candidates_path=str(visible_media_candidates_path),
        visible_screenshot_receipts_path=str(visible_screenshot_receipts_path),
        adapter_status=adapter_result.status,
        adapter_receipt_path=adapter_result.receipt_path,
        ledger_status=adapter_result.ledger_status,
        account_capture_dir=adapter_result.account_capture_dir,
        account_record_path=adapter_result.account_record_path,
        manifest_path=adapter_result.manifest_path,
        account_timeline_path=adapter_result.account_timeline_path,
        media_index_path=adapter_result.media_index_path,
        progress_events_path=adapter_result.progress_events_path,
        review_strings_path=adapter_result.review_strings_path,
        visible_record_count=len(extracted_records),
        dom_article_count=len(extracted_records),
        media_candidate_count=len(bound_media) + len(unbound_media),
        bound_media_count=len(bound_media),
        unbound_media_count=len(unbound_media),
        record_count=adapter_result.record_count,
        media_count=adapter_result.media_count,
        screenshot_count=adapter_result.screenshot_count,
        post_folder_count=adapter_result.post_folder_count,
        date_folders=adapter_result.date_folders,
        normalized_records=tuple(adapter_payload.get("normalized_records") or ()),
        side_effect_flags=build_r43z_side_effect_flags(),
        warnings=tuple(warnings),
    )
    _write_json(receipt_path, result.to_dict())
    return result


def extract_visible_dom_records_r43z(
    html_text: str,
    *,
    account_handle: str,
    account_url: str,
    capture_timestamp: str,
    html_receipt_path: str = "",
    screenshot_path: str = "",
    observed_media: Sequence[Mapping[str, Any]] = (),
    max_items: int = 5,
    include_media: bool = True,
    include_static_screenshots: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    text = html_text or ""
    matches = list(_iter_post_matches(text))
    limit = max(_safe_int(max_items, 5), 0) or len(matches)
    seen: set[str] = set()
    records: list[dict[str, Any]] = []
    bound_media: list[dict[str, Any]] = []

    for match in matches:
        if len(records) >= limit:
            break
        rkey = _safe_record_id(match["rkey"])
        if not rkey or rkey in seen:
            continue
        seen.add(rkey)
        span = _article_span_for_match(text, int(match["start"]), int(match["end"]))
        segment = text[span[0]:span[1]]
        source_url = build_bluesky_post_url_r43z(match.get("handle") or account_handle, rkey)
        visible_text = _extract_visible_text(segment) or f"Visible Bluesky post {rkey}"
        visible_timestamp = _extract_datetime(segment) or _iso_from_ts(capture_timestamp)
        media_items: list[dict[str, Any]] = []
        if include_media:
            for media_index, media_url in enumerate(_extract_media_urls(segment), start=1):
                media_item = _media_item_from_visible_dom(
                    media_url,
                    record_id=rkey,
                    source_url=source_url,
                    html_receipt_path=html_receipt_path,
                    index=media_index,
                )
                media_items.append(media_item)
                bound_media.append(media_item)
            for obs in observed_media or ():
                obs_url = _plain_url(obs.get("media_url") or obs.get("url") or obs.get("src") or "")
                obs_rkey = _safe_record_id(obs.get("rkey") or obs.get("record_id") or "")
                if obs_url and (not obs_rkey or obs_rkey == rkey):
                    media_item = _media_item_from_visible_dom(
                        obs_url,
                        record_id=rkey,
                        source_url=source_url,
                        html_receipt_path=html_receipt_path,
                        index=len(media_items) + 1,
                        observation_kind="bluesky_visible_caller_media_observation",
                    )
                    media_items.append(media_item)
                    bound_media.append(media_item)
        records.append(
            {
                "platform_id": "bluesky",
                "account_handle": _safe_handle(account_handle),
                "record_id": rkey,
                "record_type": "post",
                "source_url": source_url,
                "visible_text": visible_text,
                "visible_timestamp": visible_timestamp,
                "capture_timestamp": _safe_ts(capture_timestamp),
                "author_handle": _safe_handle(match.get("handle") or account_handle),
                "author_display_name": _extract_display_name(segment),
                "static_screenshot_path": screenshot_path if include_static_screenshots else "",
                "media_items": media_items,
                "review_strings": [f"bluesky_visible_dom|{account_handle}|{rkey}|{source_url}"],
                "observed_order": len(records) + 1,
                "platform_specific": {
                    "bluesky": {
                        "handle": _safe_handle(match.get("handle") or account_handle),
                        "rkey": rkey,
                        "app_bsky_url": source_url,
                        "visible_dom_html_receipt_path": html_receipt_path,
                        "visible_dom_article_span": list(span),
                        "visible_capture_mode": "visible_dom_evidence_import",
                        "at_uri": "",
                        "cid": "",
                        "did": "",
                    }
                },
            }
        )

    article_covered_urls = {item.get("media_url") for item in bound_media}
    unbound = []
    for url in _extract_media_urls(text):
        if url not in article_covered_urls:
            unbound.append({
                "media_url": url,
                "binding_status": "unbound_account_level_visible_dom_candidate",
                "binding_reason": "outside_post_card_or_no_visible_post_link",
                "source_observation_path": html_receipt_path,
                "metadata_only_remote_media_not_downloaded": True,
            })
    return records, bound_media, unbound


def build_bluesky_post_url_r43z(handle_or_did: str, rkey: str) -> str:
    return build_bluesky_post_url_r43v(_safe_handle(handle_or_did), _safe_record_id(rkey))


def build_fake_bluesky_visible_dom_html_r43z(account_handle: str = "example.bsky.social") -> str:
    handle = _safe_handle(account_handle or "example.bsky.social")
    return f"""<!doctype html>
<html><head><title>Fixture Bluesky visible DOM</title></head><body>
<main data-testid="profileScreen">
  <article data-testid="feedItem-by-{handle}">
    <a href="/profile/{handle}/post/3lxyzdomimagepost">post link</a>
    <span data-testid="postDisplayName">Example Bluesky</span>
    <time datetime="2026-09-18T07:35:00.000Z">Sep 18</time>
    <div data-testid="postText">Visible DOM image fixture for Bluesky capture.</div>
    <img alt="fixture visible image" src="https://cdn.bsky.app/img/feed_fullsize/plain/did:plc:r43zexample/bafkreir43zfull@jpeg" />
  </article>
  <article data-testid="feedItem-by-{handle}">
    <a href="https://bsky.app/profile/{handle}/post/3lxyzdomvideopost">post link</a>
    <span data-testid="postDisplayName">Example Bluesky</span>
    <time datetime="2026-09-18T07:36:00.000Z">Sep 18</time>
    <div data-testid="postText">Visible DOM video fixture for manifest and thumbnail receipts.</div>
    <video poster="https://video.bsky.app/watch/did:plc:r43zexample/bafkreir43zvideo/thumbnail.jpg">
      <source src="https://video.bsky.app/watch/did:plc:r43zexample/bafkreir43zvideo/playlist.m3u8" type="application/vnd.apple.mpegurl" />
    </video>
  </article>
  <img alt="account level decorative" src="https://cdn.bsky.app/img/avatar/plain/did:plc:r43zexample/avatar@jpeg" />
</main>
</body></html>"""


def build_r43z_side_effect_flags() -> dict[str, bool]:
    return {
        "bluesky_visible_dom_capture_invoked": True,
        "r43v_bluesky_adapter_used": True,
        "r43u_universal_ledger_writer_used": True,
        "visible_dom_html_receipt_written": True,
        "visible_screenshot_receipts_written": True,
        "network_actions_performed": False,
        "browser_session_started": False,
        "webview2_session_started_by_r43z": False,
        "webview2_internals_copied": False,
        "browser_profile_files_read_or_copied": False,
        "hidden_platform_api_scraping_performed": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "remote_media_downloads_performed": False,
        "source_role_checks_performed": False,
        "review_window_dependency_invoked": False,
    }


def build_report(output_root: str | Path = R43Z_DEFAULT_OUTPUT_ROOT) -> R43ZReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    result = build_bluesky_visible_dom_capture_r43z(root / "sample").run_account_export(
        BlueskyVisibleDomCaptureRequestR43Z(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260918T080000Z",
            output_root=str(root / "sample"),
            fixture_mode=True,
            explicit_live_mode=True,
            run_visible_live=True,
            include_media=True,
            include_static_screenshots=True,
            require_screenshot_receipts=True,
            max_items=5,
        )
    )
    payload = result.to_dict()
    contract = build_bluesky_visible_dom_capture_contract_r43z()
    media_index = _read_json(result.media_index_path, default=[])
    flags = build_r43z_side_effect_flags()
    checks = (
        _check("visible_dom_fixture_extracts_post_cards", result.visible_record_count == 2 and result.dom_article_count == 2),
        _check("visible_media_proximity_binding_maps_images_and_video_manifest", result.bound_media_count >= 3 and any(row.get("media_class") == "manifest" for row in media_index)),
        _check("unbound_account_level_media_is_preserved", result.unbound_media_count >= 1 and Path(result.visible_media_candidates_path).is_file()),
        _check("screenshot_receipts_are_materialized", result.screenshot_count >= 2 and Path(result.copied_screenshot_path).is_file()),
        _check("r43v_r43u_downstream_chain_passes", result.adapter_status == R43V_PASS_STATUS and result.ledger_status == R43U_PASS_STATUS and result.record_count == 2),
        _check("metadata_only_media_no_remote_downloads", all(row.get("metadata_only_remote_media_not_downloaded") is True and row.get("remote_download_performed_by_r43u") is False for row in media_index)),
        _check("no_browser_cookie_token_profile_or_network_side_effects", not any(flags[key] for key in ("network_actions_performed", "browser_session_started", "webview2_session_started_by_r43z", "webview2_internals_copied", "browser_profile_files_read_or_copied", "cookie_or_token_extraction_performed", "login_automation_performed", "captcha_or_challenge_bypass_performed", "remote_media_downloads_performed"))),
        _check("primary_receipt_files_written", all(Path(path).is_file() for path in (result.receipt_path, result.visible_dom_html_path, result.visible_dom_posts_path, result.visible_media_candidates_path, result.visible_screenshot_receipts_path, result.account_record_path, result.media_index_path))),
        _check("plain_machine_urls", _machine_urls_are_plain(payload) and _machine_urls_are_plain(contract)),
    )
    status = R43Z_PASS_STATUS if all(c["status"] == "pass" for c in checks) else R43Z_BLOCKED_STATUS
    report = R43ZReport(R43Z_MARKER, R43Z_SCHEMA_VERSION, datetime.now(timezone.utc).isoformat(), status, checks, payload, contract, flags)
    write_report(report, root)
    return report


def write_report(report: R43ZReport, output_root: str | Path = R43Z_DEFAULT_OUTPUT_ROOT) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R43Z_BLUESKY_VISIBLE_DOM_CAPTURE_LANE_REPORT.json"
    md_path = root / "R43Z_BLUESKY_VISIBLE_DOM_CAPTURE_LANE_REPORT.md"
    _write_json(json_path, report.to_dict())
    md_path.write_text(
        "\n".join([
            f"# {R43Z_MARKER}",
            "",
            f"- Status: `{report.status}`",
            f"- Schema: `{report.schema_version}`",
            f"- Generated: `{report.generated_at}`",
            "",
            "## Checks",
            *[f"- `{c.get('status')}` {c.get('name')}: {c.get('detail') or ''}".rstrip() for c in report.checks],
        ]).rstrip() + "\n",
        encoding="utf-8",
    )
    return json_path, md_path


def coerce_bluesky_visible_dom_capture_request_r43z(
    request: BlueskyVisibleDomCaptureRequestR43Z | Mapping[str, Any] | None = None,
    **overrides: Any,
) -> BlueskyVisibleDomCaptureRequestR43Z:
    data = request.to_dict() if isinstance(request, BlueskyVisibleDomCaptureRequestR43Z) else dict(request or {})
    for key, value in overrides.items():
        if value not in (None, ""):
            data[key] = value
    return BlueskyVisibleDomCaptureRequestR43Z(
        account_url=_plain_url(data.get("account_url") or ""),
        account_handle=_safe_handle(data.get("account_handle") or ""),
        capture_timestamp=_safe_ts(data.get("capture_timestamp") or ""),
        output_root=str(data.get("output_root") or R43Z_DEFAULT_OUTPUT_ROOT),
        fixture_mode=_to_bool(data.get("fixture_mode"), False),
        explicit_live_mode=_to_bool(data.get("explicit_live_mode"), False),
        run_visible_live=_to_bool(data.get("run_visible_live"), False),
        live_mode=_to_bool(data.get("live_mode"), False),
        visible_dom_html=str(data.get("visible_dom_html") or ""),
        visible_dom_html_path=str(data.get("visible_dom_html_path") or data.get("html_path") or ""),
        static_screenshot_path=str(data.get("static_screenshot_path") or data.get("screenshot_path") or ""),
        observed_media=tuple(_mapping(item) for item in (data.get("observed_media") or ())),
        include_media=_to_bool(data.get("include_media"), True),
        include_static_screenshots=_to_bool(data.get("include_static_screenshots"), True),
        require_screenshot_receipts=_to_bool(data.get("require_screenshot_receipts"), True),
        max_items=_safe_int(data.get("max_items"), 5),
        max_scrolls=_safe_int(data.get("max_scrolls"), 2),
    )


def _blocked_result(*, req: BlueskyVisibleDomCaptureRequestR43Z, root: Path, run_dir: Path, request_path: Path, receipt_path: Path, handle: str, account_url: str, capture_ts: str, html_path: Path, screenshot_path: Path | None, visible_posts_path: Path, visible_media_candidates_path: Path, visible_screenshot_receipts_path: Path, warnings: Sequence[str]) -> BlueskyVisibleDomCaptureResultR43Z:
    return BlueskyVisibleDomCaptureResultR43Z(
        marker=R43Z_MARKER,
        schema_version=R43Z_SCHEMA_VERSION,
        status=R43Z_BLOCKED_STATUS,
        account_handle=handle,
        account_url=account_url,
        capture_timestamp=capture_ts,
        output_root=str(root),
        run_dir=str(run_dir),
        request_path=str(request_path),
        receipt_path=str(receipt_path),
        visible_dom_html_path=str(html_path),
        copied_screenshot_path=str(screenshot_path) if screenshot_path else "",
        visible_dom_posts_path=str(visible_posts_path),
        visible_media_candidates_path=str(visible_media_candidates_path),
        visible_screenshot_receipts_path=str(visible_screenshot_receipts_path),
        side_effect_flags=build_r43z_side_effect_flags(),
        warnings=tuple(warnings),
    )


def _load_visible_html(req: BlueskyVisibleDomCaptureRequestR43Z) -> str:
    if req.visible_dom_html:
        return req.visible_dom_html
    path = Path(req.visible_dom_html_path) if req.visible_dom_html_path else None
    if path and path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def _materialize_visible_screenshot(req: BlueskyVisibleDomCaptureRequestR43Z, screenshot_dir: Path, *, fixture_mode: bool) -> Path | None:
    if not req.include_static_screenshots:
        return None
    supplied = Path(req.static_screenshot_path) if req.static_screenshot_path else None
    if supplied and supplied.is_file():
        target = screenshot_dir / f"visible_screenshot{supplied.suffix or '.png'}"
        shutil.copy2(supplied, target)
        return target
    if fixture_mode:
        target = screenshot_dir / "fixture_visible_screenshot.png"
        target.write_bytes(base64.b64decode(_TINY_PNG_B64))
        return target
    return None


def _iter_post_matches(text: str) -> list[dict[str, Any]]:
    pattern = re.compile(r"(?:(?:https?:)?//(?:www\.)?bsky\.app)?/profile/([^\s\"'<>?#)]+)/post/([^\s\"'<>?#)]+)", re.I)
    out: list[dict[str, Any]] = []
    for match in pattern.finditer(text or ""):
        out.append({"handle": _safe_handle(match.group(1)), "rkey": _safe_record_id(match.group(2)), "start": match.start(), "end": match.end(), "url": match.group(0)})
    return out


def _article_span_for_match(text: str, start: int, end: int) -> tuple[int, int]:
    lower = text.lower()
    article_start = lower.rfind("<article", 0, start)
    article_end = lower.find("</article>", end)
    if article_start >= 0 and article_end >= 0:
        return article_start, article_end + len("</article>")
    return max(0, start - 3000), min(len(text), end + 6000)


def _extract_visible_text(segment: str) -> str:
    cleaned = re.sub(r"(?is)<(script|style).*?</\1>", " ", segment or "")
    cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    cleaned = html_lib.unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    return cleaned[:2000]


def _extract_display_name(segment: str) -> str:
    match = re.search(r"data-testid=[\"']postDisplayName[\"'][^>]*>(.*?)</", segment or "", re.I | re.S)
    if match:
        return _extract_visible_text(match.group(1))[:200]
    return ""


def _extract_datetime(segment: str) -> str:
    match = re.search(r"datetime=[\"']([^\"']+)[\"']", segment or "", re.I)
    return _clean(match.group(1)) if match else ""


def _extract_media_urls(segment: str) -> list[str]:
    urls: list[str] = []
    for attr in ("src", "poster", "data-src", "href"):
        for match in re.finditer(attr + r"\s*=\s*[\"']([^\"']+)[\"']", segment or "", re.I):
            url = _plain_url(match.group(1))
            if _is_visible_media_url(url):
                urls.append(url)
    for match in re.finditer(r"https?://[^\s\"'<>]+", segment or "", re.I):
        url = _plain_url(match.group(0))
        if _is_visible_media_url(url):
            urls.append(url)
    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        key = url.rstrip(",.;)")
        if key not in seen:
            seen.add(key)
            deduped.append(key)
    return deduped


def _is_visible_media_url(url: str) -> bool:
    clean = _plain_url(url).lower()
    if not clean.startswith("http"):
        return False
    if any(host in clean for host in ("cdn.bsky.app", "video.bsky.app")):
        return True
    return bool(re.search(r"\.(?:jpe?g|png|webp|gif|m3u8)(?:[?#].*)?$", clean))


def _media_item_from_visible_dom(media_url: str, *, record_id: str, source_url: str, html_receipt_path: str, index: int = 1, observation_kind: str = "bluesky_visible_dom_media_candidate") -> dict[str, Any]:
    clean_url = _plain_url(media_url)
    media_class = "manifest" if ".m3u8" in clean_url.lower() else "image"
    suffix = "m3u8" if media_class == "manifest" else (_extension_from_url(clean_url).lstrip(".") or "jpg")
    return {
        "media_id": _safe_media_id(f"{record_id}_{media_class}_{clean_url}"),
        "media_class": media_class,
        "source_url": source_url,
        "media_url": clean_url,
        "local_path": "",
        "filename": f"{record_id}_visible_dom_media_{index}.{suffix}",
        "mime_type": "application/vnd.apple.mpegurl" if media_class == "manifest" else (_mime_from_url(clean_url) or "image/jpeg"),
        "byte_status": "metadata_only_visible_dom_remote_media_not_downloaded",
        "provenance": f"R43Z {observation_kind}",
        "warning": f"metadata-only Bluesky visible DOM {media_class} receipt; R43Z did not download remote media",
        "bound_to_record_id": record_id,
        "bound_to_source_url": source_url,
        "binding_status": "bound_to_post",
        "binding_reason": "bluesky_visible_dom_proximity_to_post_card",
        "source_observation_kind": observation_kind,
        "source_observation_marker": "R43Z",
        "source_observation_path": html_receipt_path,
        "metadata_only_remote_media_not_downloaded": True,
        "playlist_manifest_url": clean_url if media_class == "manifest" else "",
        "platform_specific": {"bluesky": {"r43z_visible_dom_bound": True, "dom_proximity_binding": "article_or_post_card", "visible_dom_html_receipt_path": html_receipt_path}},
    }


def _safe_record_id(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]+", "_", _clean(value)).strip("._-") or "unknown_post"


def _safe_media_id(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]+", "_", _clean(value)).strip("._-")[:240] or "unknown_media"


def _safe_handle(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]+", "_", _clean(value).strip().lstrip("@")).strip("._-") or "unknown_account"


def _safe_ts(value: Any) -> str:
    clean = _clean(value)
    return re.sub(r"[^0-9TZ]", "", clean) if clean else ""


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _iso_from_ts(ts: str) -> str:
    safe = _safe_ts(ts)
    match = re.match(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$", safe)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}T{match.group(4)}:{match.group(5)}:{match.group(6)}Z"
    return datetime.now(timezone.utc).isoformat()


def _plain_url(value: Any) -> str:
    text = _clean(value).strip("<>").replace("\\_", "_").replace("\\/", "/")
    md = re.match(r"^\[[^\]]+\]\((https?://[^)]+)\)$", text)
    return md.group(1) if md else text


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    return value


def _write_json(path: str | Path, value: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(_to_jsonable(value), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _read_json(path: str | Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def _check(name: str, ok: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": "" if ok else detail}


def _extension_from_url(url: str) -> str:
    path = urlsplit(_plain_url(url)).path.lower()
    match = re.search(r"(\.[a-z0-9]{2,5})$", path)
    if match:
        return match.group(1)
    return ""


def _mime_from_url(url: str) -> str:
    ext = _extension_from_url(url)
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".m3u8": "application/vnd.apple.mpegurl",
    }.get(ext, "")


def _machine_urls_are_plain(value: Any) -> bool:
    text = json.dumps(_to_jsonable(value), ensure_ascii=False)
    return not bool(re.search(r"\[[^\]]*https?://[^\]]+\]\(https?://", text))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R43Z Bluesky visible DOM capture lane")
    parser.add_argument("--account-url", default="https://bsky.app/profile/example.bsky.social")
    parser.add_argument("--account-handle", default="example.bsky.social")
    parser.add_argument("--capture-timestamp", default="")
    parser.add_argument("--output-root", default=R43Z_DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--html-path", default="")
    parser.add_argument("--screenshot-path", default="")
    parser.add_argument("--fixture-mode", action="store_true")
    parser.add_argument("--explicit-live-mode", action="store_true")
    parser.add_argument("--run-visible-live", action="store_true")
    parser.add_argument("--live-mode", action="store_true")
    parser.add_argument("--max-items", type=int, default=5)
    args = parser.parse_args(argv)
    if args.fixture_mode or not args.html_path:
        report = build_report(args.output_root)
        print(R43Z_MARKER)
        print(report.status)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if report.passed else 1
    result = run_bluesky_visible_dom_capture_r43z(
        BlueskyVisibleDomCaptureRequestR43Z(
            account_url=args.account_url,
            account_handle=args.account_handle,
            capture_timestamp=args.capture_timestamp,
            output_root=args.output_root,
            visible_dom_html_path=args.html_path,
            static_screenshot_path=args.screenshot_path,
            explicit_live_mode=args.explicit_live_mode,
            run_visible_live=args.run_visible_live,
            live_mode=args.live_mode,
            max_items=args.max_items,
        )
    )
    print(R43Z_MARKER)
    print(result.status)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
