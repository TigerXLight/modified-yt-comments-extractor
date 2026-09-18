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

from profile_media_universal_social_account_ledger_contract_r43u import (
    R43U_PASS_STATUS,
    UniversalSocialMediaItemR43U,
    UniversalSocialRecordR43U,
    write_universal_social_account_ledger_r43u,
)

R44D_MARKER = "YTCE_R44D_REDDIT_VISIBLE_DOM_CAPTURE_ADAPTER"
R44D_PASS_STATUS = "PASS_R44D_REDDIT_VISIBLE_DOM_CAPTURE_ADAPTER"
R44D_BLOCKED_STATUS = "BLOCKED_R44D_REDDIT_VISIBLE_DOM_CAPTURE_ADAPTER"
R44D_SCHEMA_VERSION = "reddit_visible_dom_capture_adapter.r44d.v1"
R44D_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r44d_reddit_visible_dom_capture_adapter"
R44D_MODE_ID = "reddit_visible_dom_capture_adapter"

_TINY_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="


@dataclass(frozen=True)
class RedditVisibleDomCaptureRequestR44D:
    account_url: str = ""
    account_handle: str = ""
    capture_timestamp: str = ""
    output_root: str = R44D_DEFAULT_OUTPUT_ROOT
    fixture_mode: bool = False
    explicit_live_mode: bool = False
    run_visible_live: bool = False
    live_mode: bool = False
    public_network_enabled: bool = False
    visible_dom_html: str = ""
    visible_dom_html_path: str = ""
    static_screenshot_path: str = ""
    include_posts: bool = True
    include_comments: bool = False
    include_reposts_or_reshares: bool = True
    include_media: bool = True
    include_static_screenshots: bool = True
    require_screenshot_receipts: bool = True
    feed_mode: str = "posts_and_crossposts"
    max_items: int = 5
    max_scrolls: int = 2

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class RedditVisibleDomCaptureResultR44D:
    marker: str
    schema_version: str
    status: str
    account_handle: str
    account_url: str
    navigation_url: str
    feed_mode: str
    capture_timestamp: str
    output_root: str
    run_dir: str
    request_path: str
    receipt_path: str
    visible_dom_html_path: str = ""
    copied_screenshot_path: str = ""
    visible_records_path: str = ""
    visible_media_candidates_path: str = ""
    ledger_status: str = ""
    account_capture_dir: str = ""
    account_record_path: str = ""
    manifest_path: str = ""
    account_timeline_path: str = ""
    media_index_path: str = ""
    progress_events_path: str = ""
    review_strings_path: str = ""
    visible_record_count: int = 0
    dom_record_block_count: int = 0
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
        return self.status == R44D_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R44DReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    sample_result: Mapping[str, Any]
    route_sample: Mapping[str, Any]
    contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R44D_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


class RedditVisibleDomCaptureAdapterR44D:
    """Visible-DOM Reddit adapter above the universal social ledger.

    R44D accepts visible Reddit HTML and screenshot receipts from an operator or
    later visible-browser caller. It maps submissions/crossposts/comments into
    universal post/reshare/reply records and writes them through R43U. It does
    not use Reddit credentials, cookies, browser profile files, hidden APIs,
    challenge bypass, or remote media downloads.
    """

    def __init__(self, output_root: str | Path = R44D_DEFAULT_OUTPUT_ROOT) -> None:
        self.output_root = Path(output_root)

    def run_account_export(
        self,
        request: RedditVisibleDomCaptureRequestR44D | Mapping[str, Any] | None = None,
        **overrides: Any,
    ) -> RedditVisibleDomCaptureResultR44D:
        req = coerce_reddit_visible_dom_capture_request_r44d(request, **overrides)
        return run_reddit_visible_dom_capture_r44d(req, output_root=self.output_root)


def build_reddit_visible_dom_capture_r44d(output_root: str | Path = R44D_DEFAULT_OUTPUT_ROOT) -> RedditVisibleDomCaptureAdapterR44D:
    return RedditVisibleDomCaptureAdapterR44D(output_root=output_root)


def build_reddit_visible_dom_capture_contract_r44d() -> dict[str, Any]:
    return {
        "marker": R44D_MARKER,
        "schema_version": R44D_SCHEMA_VERSION,
        "mode_id": R44D_MODE_ID,
        "twitter_x_parity_terms": {
            "posts_and_retweets": "Reddit submissions plus crossposts",
            "posts_and_replies": "Reddit submissions plus comments",
        },
        "visible_browser_modes": {
            "posts_and_crossposts": "navigate the user's submitted timeline and preserve visible post text, media, crosspost hints and screenshots",
            "posts_and_comments": "navigate the user's comments timeline and preserve visible comment text, linked post context, media and screenshots",
            "single_thread": "preserve the exact /r/<subreddit>/comments/<post_id>/... URL and capture visible thread records",
        },
        "navigation_rule": {
            "posts_and_crossposts": "https://www.reddit.com/user/<handle>/submitted/",
            "posts_and_comments": "https://www.reddit.com/user/<handle>/comments/",
            "single_thread": "preserve supplied Reddit thread/comment URL exactly",
        },
        "record_mapping": {
            "reddit_submission": "post",
            "reddit_crosspost": "repost_or_reshare",
            "reddit_comment": "reply",
        },
        "media_mapping": {
            "i.redd.it/preview.redd.it/redditmedia image URLs": "image metadata-only media receipts",
            "v.redd.it/mp4/m3u8 URLs": "video or manifest metadata-only media receipts",
            "external links/cards": "external metadata-only media receipts",
        },
        "ledger_contract": "same R43U account/date/post/media/screenshot ledger used for text, media, crossposts and comments",
        "no_remote_media_downloads": True,
        "no_cookie_token_or_browser_profile_copying": True,
        "hidden_platform_api_scraping_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
    }


def run_reddit_visible_dom_capture_r44d(
    request: RedditVisibleDomCaptureRequestR44D | Mapping[str, Any] | None = None,
    *,
    output_root: str | Path = R44D_DEFAULT_OUTPUT_ROOT,
) -> RedditVisibleDomCaptureResultR44D:
    req = coerce_reddit_visible_dom_capture_request_r44d(request)
    root = Path(req.output_root or output_root or R44D_DEFAULT_OUTPUT_ROOT)
    capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
    account_url = _plain_url(req.account_url)
    handle = _safe_reddit_handle(req.account_handle or _reddit_handle_from_url(account_url) or "example_redditor")
    feed_mode = normalize_reddit_feed_mode_r44d(req.feed_mode, include_comments=req.include_comments, include_reposts_or_reshares=req.include_reposts_or_reshares)
    navigation_url = build_reddit_visible_navigation_url_r44d(account_url, handle, feed_mode)
    if not account_url:
        account_url = navigation_url

    run_dir = root / handle / f"reddit_visible_dom_capture_{capture_ts}"
    evidence_dir = run_dir / "visible_reddit_evidence"
    screenshot_dir = run_dir / "visible_screenshot_receipts"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    request_path = run_dir / "r44d_reddit_visible_dom_capture_request.json"
    receipt_path = run_dir / "r44d_reddit_visible_dom_capture_receipt.json"
    visible_records_path = run_dir / "visible_reddit_records.json"
    visible_media_candidates_path = run_dir / "visible_reddit_media_candidates.json"
    _write_json(request_path, {**req.to_dict(), "navigation_url": navigation_url, "feed_mode": feed_mode})

    warnings: list[str] = []
    html_text = _load_visible_html(req)
    if req.fixture_mode and not html_text:
        html_text = build_fake_reddit_visible_dom_html_r44d(account_handle=handle, feed_mode=feed_mode)
    html_path = evidence_dir / "visible_dom.html"
    html_path.write_text(html_text, encoding="utf-8")

    screenshot_path = _materialize_screenshot(req, screenshot_dir, fixture_mode=req.fixture_mode)
    if req.include_static_screenshots and req.require_screenshot_receipts and not screenshot_path:
        warnings.append("R44D requires screenshot receipts but no screenshot file was supplied or generated.")

    records, media_candidates = extract_reddit_visible_records_from_dom_r44d(
        html_text,
        account_handle=handle,
        account_url=account_url,
        navigation_url=navigation_url,
        capture_timestamp=capture_ts,
        html_receipt_path=str(html_path),
        screenshot_path=str(screenshot_path) if screenshot_path else "",
        feed_mode=feed_mode,
        include_media=req.include_media,
        include_static_screenshots=req.include_static_screenshots,
        max_items=req.max_items,
    )
    _write_json(visible_records_path, [r.to_dict() for r in records])
    _write_json(visible_media_candidates_path, media_candidates)

    if not records:
        warnings.append("No Reddit visible DOM records were extracted.")
        result = _blocked_result(
            req=req,
            root=root,
            run_dir=run_dir,
            request_path=request_path,
            receipt_path=receipt_path,
            handle=handle,
            account_url=account_url,
            navigation_url=navigation_url,
            feed_mode=feed_mode,
            capture_ts=capture_ts,
            html_path=html_path,
            screenshot_path=screenshot_path,
            visible_records_path=visible_records_path,
            visible_media_candidates_path=visible_media_candidates_path,
            warnings=warnings,
        )
        _write_json(receipt_path, result.to_dict())
        return result

    ledger = write_universal_social_account_ledger_r43u(
        records,
        output_root=run_dir / "r43u_ledger",
        platform_id="reddit",
        account_handle=handle,
        capture_timestamp=capture_ts,
    )
    ledger_payload = ledger.to_dict()
    flags = build_r44d_side_effect_flags()
    status = R44D_PASS_STATUS if ledger.status == R43U_PASS_STATUS and ledger.record_count > 0 and (not req.require_screenshot_receipts or ledger.screenshot_count > 0) else R44D_BLOCKED_STATUS
    if status != R44D_PASS_STATUS:
        warnings.append(f"Reddit downstream R43U ledger did not pass sufficiently: {ledger.status!r}.")

    result = RedditVisibleDomCaptureResultR44D(
        marker=R44D_MARKER,
        schema_version=R44D_SCHEMA_VERSION,
        status=status,
        account_handle=handle,
        account_url=account_url,
        navigation_url=navigation_url,
        feed_mode=feed_mode,
        capture_timestamp=capture_ts,
        output_root=str(root),
        run_dir=str(run_dir),
        request_path=str(request_path),
        receipt_path=str(receipt_path),
        visible_dom_html_path=str(html_path),
        copied_screenshot_path=str(screenshot_path) if screenshot_path else "",
        visible_records_path=str(visible_records_path),
        visible_media_candidates_path=str(visible_media_candidates_path),
        ledger_status=ledger.status,
        account_capture_dir=str(ledger.account_capture_dir),
        account_record_path=str(ledger.account_record_path),
        manifest_path=str(ledger.manifest_path),
        account_timeline_path=str(ledger.account_timeline_path),
        media_index_path=str(ledger.media_index_path),
        progress_events_path=str(ledger.progress_events_path),
        review_strings_path=str(ledger.review_strings_path),
        visible_record_count=len(records),
        dom_record_block_count=int(media_candidates.get("dom_record_block_count", len(records))),
        media_candidate_count=int(media_candidates.get("media_candidate_count", 0)),
        bound_media_count=int(media_candidates.get("bound_media_count", 0)),
        unbound_media_count=int(media_candidates.get("unbound_media_count", 0)),
        record_count=ledger.record_count,
        media_count=ledger.media_count,
        screenshot_count=ledger.screenshot_count,
        post_folder_count=ledger.post_folder_count,
        date_folders=tuple(ledger.date_folders),
        normalized_records=tuple(r.to_dict() for r in records),
        side_effect_flags=flags,
        warnings=tuple(warnings + list(ledger_payload.get("warnings") or ())),
    )
    _write_json(receipt_path, result.to_dict())
    return result


def build_report(output_root: str | Path = R44D_DEFAULT_OUTPUT_ROOT) -> R44DReport:
    root = Path(output_root)
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    sample = run_reddit_visible_dom_capture_r44d(
        RedditVisibleDomCaptureRequestR44D(
            account_url="https://www.reddit.com/user/example_redditor/",
            account_handle="example_redditor",
            capture_timestamp="20260918T103000Z",
            output_root=str(root / "sample"),
            fixture_mode=True,
            feed_mode="posts_and_comments",
            include_comments=True,
            include_media=True,
            max_items=5,
        )
    )
    route_sample = _run_r43e_route_sample(root / "route_sample")
    contract = build_reddit_visible_dom_capture_contract_r44d()
    flags = build_r44d_side_effect_flags()
    record_types = [row.get("record_type") for row in sample.to_dict().get("normalized_records", [])]
    checks = (
        _check("fixture_extracts_reddit_submission_comment_and_crosspost", sample.status == R44D_PASS_STATUS and {"post", "reply", "repost_or_reshare"} <= set(record_types)),
        _check("visible_media_bound_to_reddit_records", sample.media_count >= 4 and sample.bound_media_count >= 4),
        _check("reddit_comments_mode_navigation_uses_comments_tab", sample.feed_mode == "posts_and_comments" and sample.navigation_url.endswith("/comments/")),
        _check("reddit_single_thread_url_is_preserved", build_reddit_visible_navigation_url_r44d("https://www.reddit.com/r/example/comments/abc123/title/", "example", "posts_and_comments").endswith("/comments/abc123/title/")),
        _check("route_registry_reaches_reddit_adapter", route_sample.get("status") == "PASS_R43E_UNIVERSAL_SOCIAL_ACCOUNT_TRACKING_CONTRACT_ADAPTER_MAP" and route_sample.get("downstream_status") == R44D_PASS_STATUS),
        _check("r43u_universal_ledger_written", sample.ledger_status == R43U_PASS_STATUS and bool(sample.account_record_path) and bool(sample.media_index_path)),
        _check("no_browser_cookie_token_profile_or_network_side_effects", not any(flags.get(k) for k in ("browser_session_started", "network_actions_performed", "browser_profile_files_read_or_copied", "cookie_or_token_extraction_performed", "remote_media_downloads_performed"))),
        _check("plain_machine_urls", _machine_urls_are_plain(sample.to_dict()) and _machine_urls_are_plain(route_sample) and _machine_urls_are_plain(contract)),
    )
    status = R44D_PASS_STATUS if all(c["status"] == "pass" for c in checks) else R44D_BLOCKED_STATUS
    report = R44DReport(
        marker=R44D_MARKER,
        schema_version=R44D_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=checks,
        sample_result=sample.to_dict(),
        route_sample=route_sample,
        contract=contract,
        side_effect_flags=flags,
    )
    write_report(report, root)
    return report


def _run_r43e_route_sample(root: Path) -> dict[str, Any]:
    from profile_media_universal_social_account_tracking_r43e import (
        UniversalSocialAccountTrackingRequestR43E,
        build_universal_social_account_tracking_registry_r43e,
    )

    registry = build_universal_social_account_tracking_registry_r43e(output_root=root)
    result = registry.run_account_export(
        UniversalSocialAccountTrackingRequestR43E(
            platform_id="reddit",
            account_url="https://www.reddit.com/user/example_redditor/",
            account_handle="example_redditor",
            capture_timestamp="20260918T103100Z",
            output_root=str(root),
            fixture_mode=True,
            include_replies=True,
            max_items=5,
        )
    )
    return result.to_dict()


def extract_reddit_visible_records_from_dom_r44d(
    html_text: str,
    *,
    account_handle: str,
    account_url: str,
    navigation_url: str = "",
    capture_timestamp: str = "",
    html_receipt_path: str = "",
    screenshot_path: str = "",
    feed_mode: str = "posts_and_crossposts",
    include_media: bool = True,
    include_static_screenshots: bool = True,
    max_items: int = 5,
) -> tuple[tuple[UniversalSocialRecordR43U, ...], dict[str, Any]]:
    html_text = str(html_text or "")
    blocks = _extract_reddit_blocks(html_text)
    records: list[UniversalSocialRecordR43U] = []
    candidates: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, block in enumerate(blocks, start=1):
        kind = _record_kind_from_block(block)
        if feed_mode == "posts_and_crossposts" and kind == "comment":
            # Keep explicit thread comments when the supplied URL is a thread, but
            # do not treat user comments as timeline posts in submitted mode.
            if not _is_reddit_thread_url(account_url):
                continue
        if feed_mode == "posts_and_comments" and kind == "crosspost":
            # Comments mode still may include a linked/crossposted parent on Reddit;
            # preserve it only when it is visibly rendered as its own block.
            pass
        record_type = "reply" if kind == "comment" else ("repost_or_reshare" if kind == "crosspost" else "post")
        source_url = _best_reddit_permalink(block, fallback=account_url or navigation_url)
        record_id = _safe_id(_record_id_from_block(block, source_url=source_url, fallback=f"reddit_{index:03d}"))
        if not record_id or record_id in seen_ids:
            record_id = _safe_id(f"{record_id or 'reddit'}_{index:03d}")
        seen_ids.add(record_id)
        visible_text = _visible_text_from_block(block) or _title_from_url(source_url) or f"Reddit {kind} visible record"
        visible_timestamp = _timestamp_from_block(block)
        author = _author_from_block(block, default=account_handle)
        media_items: list[UniversalSocialMediaItemR43U] = []
        if include_media:
            for media_index, media_url in enumerate(_extract_media_urls(block), start=1):
                media_class = _classify_media_url(media_url)
                media_id = _safe_id(f"{record_id}_{media_class}_{media_index:03d}")
                candidates.append({
                    "media_id": media_id,
                    "record_id": record_id,
                    "media_url": media_url,
                    "media_class": media_class,
                    "binding_status": "bound_to_reddit_record_by_dom_proximity",
                    "source_observation_path": html_receipt_path,
                })
                media_items.append(
                    UniversalSocialMediaItemR43U(
                        media_id=media_id,
                        media_class=media_class,
                        source_url=source_url,
                        media_url=media_url,
                        filename=_filename_from_url(media_url) or f"{media_id}.url",
                        provenance="R44D visible Reddit DOM media candidate bound by record-block proximity",
                        warning="metadata-only Reddit media receipt; R44D/R43U did not download remote media",
                        bound_to_record_id=record_id,
                        bound_to_source_url=source_url,
                        binding_status="bound_to_post",
                        binding_reason="reddit_visible_dom_record_proximity",
                        source_observation_kind="visible_reddit_dom",
                        source_observation_marker=R44D_MARKER,
                        source_observation_path=html_receipt_path,
                        metadata_only_remote_media_not_downloaded=True,
                        playlist_manifest_url=media_url if media_class == "manifest" else "",
                        platform_specific={"reddit": {"record_kind": kind, "permalink": source_url, "media_host": _host(media_url)}},
                    )
                )
        original_record_id = _original_id_from_block(block) if record_type == "repost_or_reshare" else ""
        records.append(
            UniversalSocialRecordR43U(
                platform_id="reddit",
                account_handle=account_handle,
                record_id=record_id,
                record_type=record_type,
                source_url=source_url,
                visible_text=visible_text,
                visible_timestamp=visible_timestamp,
                capture_timestamp=capture_timestamp,
                author_handle=author,
                author_display_name=author,
                original_record_id=original_record_id,
                reshared_by_handle=account_handle if record_type == "repost_or_reshare" else "",
                reshare_context={"reddit_crosspost": True, "original_record_id": original_record_id} if record_type == "repost_or_reshare" else {},
                static_screenshot_path=screenshot_path if include_static_screenshots else "",
                media_items=tuple(media_items),
                review_strings=tuple(_review_strings_for_record(visible_text, source_url, record_type)),
                observed_order=index,
                platform_specific={
                    "reddit": {
                        "record_kind": kind,
                        "permalink": source_url,
                        "navigation_url": navigation_url,
                        "feed_mode": feed_mode,
                        "subreddit": _subreddit_from_url(source_url),
                        "comment_id": _comment_id_from_url(source_url),
                        "post_id": _post_id_from_url(source_url),
                    }
                },
            )
        )
        if len(records) >= max(1, int(max_items or 1)):
            break
    payload = {
        "dom_record_block_count": len(blocks),
        "media_candidate_count": len(candidates),
        "bound_media_count": len(candidates),
        "unbound_media_count": 0,
        "candidates": candidates,
    }
    return tuple(records), payload


def build_reddit_visible_navigation_url_r44d(account_url: str, account_handle: str, feed_mode: str = "posts_and_crossposts") -> str:
    url = _plain_url(account_url)
    mode = normalize_reddit_feed_mode_r44d(feed_mode)
    if _is_reddit_thread_url(url):
        return url
    handle = _safe_reddit_handle(account_handle or _reddit_handle_from_url(url) or "example_redditor")
    if mode == "posts_and_comments":
        return f"https://www.reddit.com/user/{handle}/comments/"
    return f"https://www.reddit.com/user/{handle}/submitted/"


def normalize_reddit_feed_mode_r44d(feed_mode: str, *, include_comments: bool = False, include_reposts_or_reshares: bool = True) -> str:
    text = _clean(feed_mode).lower().replace("-", "_").replace(" ", "_")
    if text in {"comments", "posts_and_comments", "posts_and_replies", "replies"} or include_comments:
        return "posts_and_comments"
    if text in {"single", "single_thread", "thread", "comment_thread"}:
        return "single_thread"
    return "posts_and_crossposts" if include_reposts_or_reshares else "posts_only"


def build_fake_reddit_visible_dom_html_r44d(account_handle: str = "example_redditor", feed_mode: str = "posts_and_comments") -> str:
    return f"""
<html><body>
<article data-reddit-record-kind="submission" data-reddit-id="abc123" data-author="{account_handle}">
  <a data-testid="post-title" href="https://www.reddit.com/r/example/comments/abc123/example_post_title/">Example Reddit image submission title</a>
  <time datetime="2026-09-18T10:30:00Z">18 Sep 2026</time>
  <p>This is visible selftext from a Reddit submission.</p>
  <img src="https://i.redd.it/example_image_one.jpg" alt="first image">
  <a href="https://preview.redd.it/example_preview.png?width=960&format=png&auto=webp&s=abc">preview image</a>
</article>
<article data-reddit-record-kind="crosspost" data-reddit-id="cross789" data-crosspost-parent="orig456" data-author="{account_handle}">
  <a href="https://www.reddit.com/r/example/comments/cross789/crossposted_thread/">Crossposted Reddit video thread</a>
  <time datetime="2026-09-18T10:31:00Z">18 Sep 2026</time>
  <p>Visible crosspost context text.</p>
  <video poster="https://external-preview.redd.it/poster.jpg"><source src="https://v.redd.it/examplevideo/DASHPlaylist.mpd" type="application/dash+xml"></video>
</article>
<article data-reddit-record-kind="comment" data-reddit-id="cmt555" data-author="commenter_example">
  <a href="https://www.reddit.com/r/example/comments/abc123/example_post_title/comment/cmt555/">Example visible Reddit comment permalink</a>
  <time datetime="2026-09-18T10:32:00Z">18 Sep 2026</time>
  <p>This is a visible Reddit comment/reply with a linked media URL.</p>
  <a href="https://i.redd.it/comment_image.webp">comment image</a>
</article>
</body></html>
""".strip()


def build_r44d_side_effect_flags() -> dict[str, bool]:
    return {
        "reddit_visible_dom_capture_adapter_invoked": True,
        "browser_session_started": False,
        "network_actions_performed": False,
        "browser_profile_files_read_or_copied": False,
        "webview2_internals_copied": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "remote_media_downloads_performed": False,
        "r43u_universal_ledger_writer_used": True,
        "source_role_checks_performed": False,
        "review_window_dependency_invoked": False,
    }


def write_report(report: R44DReport, output_root: str | Path) -> None:
    root = Path(output_root)
    _write_json(root / "R44D_REDDIT_VISIBLE_DOM_CAPTURE_ADAPTER_REPORT.json", report.to_dict())
    _write_text(root / "R44D_REDDIT_VISIBLE_DOM_CAPTURE_ADAPTER_REPORT.md", _report_md(report))


def coerce_reddit_visible_dom_capture_request_r44d(
    request: RedditVisibleDomCaptureRequestR44D | Mapping[str, Any] | None = None,
    **overrides: Any,
) -> RedditVisibleDomCaptureRequestR44D:
    if isinstance(request, RedditVisibleDomCaptureRequestR44D):
        base = request.to_dict()
    elif hasattr(request, "to_dict"):
        payload = request.to_dict()
        base = dict(payload) if isinstance(payload, Mapping) else {}
    elif isinstance(request, Mapping):
        base = dict(request)
    else:
        base = {}
    for key, value in overrides.items():
        if value not in (None, ""):
            base[key] = value
    return RedditVisibleDomCaptureRequestR44D(
        account_url=_plain_url(base.get("account_url") or ""),
        account_handle=_safe_reddit_handle(base.get("account_handle") or ""),
        capture_timestamp=_safe_ts(base.get("capture_timestamp") or ""),
        output_root=_clean(base.get("output_root") or R44D_DEFAULT_OUTPUT_ROOT),
        fixture_mode=_to_bool(base.get("fixture_mode"), False),
        explicit_live_mode=_to_bool(base.get("explicit_live_mode"), False),
        run_visible_live=_to_bool(base.get("run_visible_live"), False),
        live_mode=_to_bool(base.get("live_mode"), False),
        public_network_enabled=_to_bool(base.get("public_network_enabled"), False),
        visible_dom_html=str(base.get("visible_dom_html") or ""),
        visible_dom_html_path=_clean(base.get("visible_dom_html_path") or ""),
        static_screenshot_path=_clean(base.get("static_screenshot_path") or ""),
        include_posts=_to_bool(base.get("include_posts"), True),
        include_comments=_to_bool(base.get("include_comments", base.get("include_replies")), False),
        include_reposts_or_reshares=_to_bool(base.get("include_reposts_or_reshares", base.get("include_reposts")), True),
        include_media=_to_bool(base.get("include_media"), True),
        include_static_screenshots=_to_bool(base.get("include_static_screenshots"), True),
        require_screenshot_receipts=_to_bool(base.get("require_screenshot_receipts"), True),
        feed_mode=_clean(base.get("feed_mode") or ""),
        max_items=max(1, _safe_int(base.get("max_items"), 5)),
        max_scrolls=max(0, _safe_int(base.get("max_scrolls"), 2)),
    )


def _extract_reddit_blocks(html_text: str) -> list[str]:
    pattern = re.compile(r"<(article|shreddit-post|shreddit-comment)\b[^>]*>.*?</\1>", re.I | re.S)
    blocks = [m.group(0) for m in pattern.finditer(html_text or "")]
    if blocks:
        return blocks
    # Fallback: split around visible Reddit permalinks so pasted/simple HTML can still be ingested.
    chunks = re.split(r"(?=<a\b[^>]+href=['\"]https?://(?:www\.)?reddit\.com/r/[^'\"]+/comments/)", html_text or "", flags=re.I)
    return [chunk for chunk in chunks if "/comments/" in chunk.lower()][:25]


def _record_kind_from_block(block: str) -> str:
    text = block.lower()
    match = re.search(r"data-reddit-record-kind=['\"]([^'\"]+)", block, re.I)
    if match:
        value = match.group(1).lower()
        if "comment" in value:
            return "comment"
        if "cross" in value:
            return "crosspost"
        return "submission"
    if "shreddit-comment" in text or "data-testid=\"comment" in text or "/comment/" in text:
        return "comment"
    if "crosspost" in text or "data-crosspost-parent" in text:
        return "crosspost"
    return "submission"


def _best_reddit_permalink(block: str, *, fallback: str) -> str:
    for url in _extract_urls(block):
        lower = url.lower()
        if "reddit.com/r/" in lower and "/comments/" in lower:
            return _normalize_reddit_url(url)
    return _plain_url(fallback)


def _record_id_from_block(block: str, *, source_url: str, fallback: str) -> str:
    for attr in ("data-reddit-id", "data-fullname", "data-click-id", "id"):
        match = re.search(attr + r"=['\"]([^'\"]+)", block, re.I)
        if match and _clean(match.group(1)):
            value = match.group(1)
            if value.startswith("t3_") or value.startswith("t1_"):
                value = value[3:]
            return value
    return _comment_id_from_url(source_url) or _post_id_from_url(source_url) or fallback


def _original_id_from_block(block: str) -> str:
    match = re.search(r"data-crosspost-parent=['\"]([^'\"]+)", block, re.I)
    return _safe_id(match.group(1)) if match else ""


def _visible_text_from_block(block: str) -> str:
    cleaned = re.sub(r"<script\b.*?</script>", " ", block, flags=re.I | re.S)
    cleaned = re.sub(r"<style\b.*?</style>", " ", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return _clean(html_lib.unescape(cleaned))


def _timestamp_from_block(block: str) -> str:
    for pattern in (r"datetime=['\"]([^'\"]+)", r"created-utc=['\"]([^'\"]+)", r"data-created=['\"]([^'\"]+)"):
        match = re.search(pattern, block, re.I)
        if match:
            return _clean(match.group(1))
    return ""


def _author_from_block(block: str, *, default: str) -> str:
    for pattern in (r"data-author=['\"]/?u/?([^'\"]+)", r"author=['\"]/?u/?([^'\"]+)", r"/user/([^/?#'\"]+)"):
        match = re.search(pattern, block, re.I)
        if match:
            return _safe_reddit_handle(match.group(1))
    return _safe_reddit_handle(default)


def _extract_media_urls(block: str) -> list[str]:
    urls = []
    for url in _extract_urls(block):
        if _is_media_url(url):
            urls.append(url)
    output: list[str] = []
    seen: set[str] = set()
    for url in urls:
        plain = _plain_url(html_lib.unescape(url))
        if plain and plain not in seen:
            seen.add(plain)
            output.append(plain)
    return output


def _extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    for match in re.finditer(r"(?:href|src|poster)=['\"]([^'\"]+)['\"]", text or "", re.I):
        urls.append(_plain_url(html_lib.unescape(match.group(1))))
    for match in re.finditer(r"https?://[^\s<'\"]+", text or "", re.I):
        urls.append(_plain_url(html_lib.unescape(match.group(0))))
    return urls


def _is_media_url(url: str) -> bool:
    lower = _plain_url(url).lower()
    host = _host(lower)
    if host.endswith(("i.redd.it", "preview.redd.it", "external-preview.redd.it", "redditmedia.com", "redd.it")):
        return True
    if host.endswith("v.redd.it"):
        return True
    return bool(re.search(r"\.(?:jpg|jpeg|png|webp|gif|mp4|m3u8|mpd)(?:[?#].*)?$", lower))


def _classify_media_url(url: str) -> str:
    lower = _plain_url(url).lower()
    if "m3u8" in lower or lower.endswith(".mpd") or "dashplaylist" in lower:
        return "manifest"
    if _host(lower).endswith("v.redd.it") or re.search(r"\.(?:mp4)(?:[?#].*)?$", lower):
        return "video"
    if re.search(r"\.(?:jpg|jpeg|png|webp|gif)(?:[?#].*)?$", lower) or _host(lower).endswith(("i.redd.it", "preview.redd.it", "external-preview.redd.it", "redditmedia.com")):
        return "image"
    return "external"


def _review_strings_for_record(text: str, source_url: str, record_type: str) -> list[str]:
    strings = []
    if text:
        strings.append(text)
    if source_url:
        strings.append(f"Reddit {record_type} source: {source_url}")
    return strings


def _load_visible_html(req: RedditVisibleDomCaptureRequestR44D) -> str:
    if req.visible_dom_html:
        return str(req.visible_dom_html)
    if req.visible_dom_html_path:
        path = Path(req.visible_dom_html_path)
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def _materialize_screenshot(req: RedditVisibleDomCaptureRequestR44D, screenshot_dir: Path, *, fixture_mode: bool) -> Path | None:
    if not req.include_static_screenshots:
        return None
    if req.static_screenshot_path:
        src = Path(req.static_screenshot_path)
        if src.is_file():
            target = screenshot_dir / (_safe_filename(src.name) or "visible_reddit_screenshot.png")
            shutil.copy2(src, target)
            return target
    if fixture_mode:
        target = screenshot_dir / "visible_reddit_fixture_screenshot.png"
        target.write_bytes(base64.b64decode(_TINY_PNG_B64))
        return target
    return None


def _blocked_result(**kwargs: Any) -> RedditVisibleDomCaptureResultR44D:
    req = kwargs["req"]
    return RedditVisibleDomCaptureResultR44D(
        marker=R44D_MARKER,
        schema_version=R44D_SCHEMA_VERSION,
        status=R44D_BLOCKED_STATUS,
        account_handle=kwargs["handle"],
        account_url=kwargs["account_url"],
        navigation_url=kwargs["navigation_url"],
        feed_mode=kwargs["feed_mode"],
        capture_timestamp=kwargs["capture_ts"],
        output_root=str(kwargs["root"]),
        run_dir=str(kwargs["run_dir"]),
        request_path=str(kwargs["request_path"]),
        receipt_path=str(kwargs["receipt_path"]),
        visible_dom_html_path=str(kwargs["html_path"]),
        copied_screenshot_path=str(kwargs["screenshot_path"] or ""),
        visible_records_path=str(kwargs["visible_records_path"]),
        visible_media_candidates_path=str(kwargs["visible_media_candidates_path"]),
        side_effect_flags=build_r44d_side_effect_flags(),
        warnings=tuple(kwargs.get("warnings") or ()),
    )


def _run_cli() -> int:
    parser = argparse.ArgumentParser(description="R44D Reddit visible DOM capture adapter")
    parser.add_argument("--account-url", default="https://www.reddit.com/user/example_redditor/")
    parser.add_argument("--account-handle", default="example_redditor")
    parser.add_argument("--output-root", default=R44D_DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--capture-timestamp", default="")
    parser.add_argument("--visible-dom-html-path", default="")
    parser.add_argument("--static-screenshot-path", default="")
    parser.add_argument("--feed-mode", default="posts_and_comments")
    parser.add_argument("--max-items", type=int, default=5)
    parser.add_argument("--fixture-mode", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.report:
        report = build_report(args.output_root)
        print(R44D_MARKER)
        print(report.status)
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0 if report.passed else 1
    result = run_reddit_visible_dom_capture_r44d(
        RedditVisibleDomCaptureRequestR44D(
            account_url=args.account_url,
            account_handle=args.account_handle,
            output_root=args.output_root,
            capture_timestamp=args.capture_timestamp,
            visible_dom_html_path=args.visible_dom_html_path,
            static_screenshot_path=args.static_screenshot_path,
            feed_mode=args.feed_mode,
            fixture_mode=args.fixture_mode or not args.visible_dom_html_path,
            include_comments=args.feed_mode in {"posts_and_comments", "comments", "posts_and_replies"},
            max_items=args.max_items,
        )
    )
    print(R44D_MARKER)
    print(result.status)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.passed else 1


def _report_md(report: R44DReport) -> str:
    lines = [
        "# R44D Reddit Visible DOM Capture Adapter",
        "",
        f"Status: `{report.status}`",
        f"Marker: `{report.marker}`",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.append(f"- {check.get('status')}: {check.get('name')}")
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Records: `{report.sample_result.get('record_count')}`",
        f"- Media: `{report.sample_result.get('media_count')}`",
        f"- Screenshots: `{report.sample_result.get('screenshot_count')}`",
        f"- Route downstream: `{report.route_sample.get('downstream_status')}`",
        "",
    ])
    return "\n".join(lines)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


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
    match = re.fullmatch(r"\[[^\]]+\]\((https?://[^\s)]+)\)", text)
    if match:
        return match.group(1)
    return text.replace("\\_", "_").replace("\\:", ":")


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_ts(value: Any) -> str:
    text = _clean(value).replace(":", "").replace("-", "")
    return re.sub(r"[^0-9TZ]", "", text)


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_reddit_handle(value: Any) -> str:
    text = _clean(value).strip().lstrip("u/").lstrip("/").replace("u/", "")
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._-")
    return text or "unknown_reddit_account"


def _safe_id(value: Any) -> str:
    text = _clean(value)
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._-")
    return text or "unknown_record"


def _safe_filename(value: Any) -> str:
    text = _clean(value)
    text = re.sub(r"[<>:\"/\\|?*\x00-\x1F]+", "_", text).strip("._ ")
    return text or "reddit_receipt"


def _filename_from_url(url: str) -> str:
    path = urlsplit(_plain_url(url)).path.rsplit("/", 1)[-1]
    return _safe_filename(path) if path else ""


def _host(url: str) -> str:
    try:
        return urlsplit(_plain_url(url)).netloc.lower().split(":", 1)[0]
    except Exception:
        return ""


def _normalize_reddit_url(url: str) -> str:
    text = _plain_url(url)
    if text.startswith("/"):
        return "https://www.reddit.com" + text
    return text


def _is_reddit_thread_url(url: str) -> bool:
    lower = _plain_url(url).lower()
    return "reddit.com/r/" in lower and "/comments/" in lower


def _reddit_handle_from_url(url: str) -> str:
    text = _plain_url(url)
    match = re.search(r"reddit\.com/(?:user|u)/([^/?#]+)", text, re.I)
    if match:
        return _safe_reddit_handle(match.group(1))
    match = re.search(r"reddit\.com/r/([^/?#]+)", text, re.I)
    if match:
        return _safe_reddit_handle("r_" + match.group(1))
    return ""


def _post_id_from_url(url: str) -> str:
    match = re.search(r"/comments/([^/?#]+)", _plain_url(url), re.I)
    return _safe_id(match.group(1)) if match else ""


def _comment_id_from_url(url: str) -> str:
    match = re.search(r"/comment/([^/?#]+)", _plain_url(url), re.I)
    return _safe_id(match.group(1)) if match else ""


def _subreddit_from_url(url: str) -> str:
    match = re.search(r"reddit\.com/r/([^/?#]+)", _plain_url(url), re.I)
    return _safe_id(match.group(1)) if match else ""


def _title_from_url(url: str) -> str:
    bits = [b for b in urlsplit(_plain_url(url)).path.split("/") if b]
    if len(bits) >= 4 and bits[0].lower() == "r" and bits[2].lower() == "comments":
        return bits[4].replace("_", " ") if len(bits) > 4 else ""
    return ""


if __name__ == "__main__":
    raise SystemExit(_run_cli())
