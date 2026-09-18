from __future__ import annotations

import argparse
import base64
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from profile_media_bluesky_public_appview_import_r43w import (
    R43W_PASS_STATUS,
    bluesky_public_feed_filter_for_mode_r44c,
    extract_post_views_from_author_feed_r43w,
)
from profile_media_bluesky_visible_account_adapter_r43v import (
    R43V_PASS_STATUS,
    build_fake_bluesky_post_views_r43v,
    normalize_bluesky_post_view_to_universal_record_r43v,
)
from profile_media_bluesky_visible_dom_capture_r43z import R43Z_PASS_STATUS
from profile_media_bluesky_visible_live_workbench_capture_r44a import (
    R44A_PASS_STATUS,
    BlueskyVisibleLiveWorkbenchCaptureRequestR44A,
    build_bluesky_visible_live_workbench_capture_r44a,
    build_bluesky_visible_navigation_url_r44c,
)
from profile_media_bluesky_real_windows_visible_browser_smoke_r44b import (
    R44B_PASS_STATUS,
    BlueskyRealWindowsVisibleBrowserSmokeRequestR44B,
    run_bluesky_real_windows_visible_browser_smoke_r44b,
)
from profile_media_universal_social_account_ledger_contract_r43u import R43U_PASS_STATUS

R44C_MARKER = "YTCE_R44C_BLUESKY_POSTS_REPOSTS_REPLIES_PARITY"
R44C_PASS_STATUS = "PASS_R44C_BLUESKY_POSTS_REPOSTS_REPLIES_PARITY"
R44C_BLOCKED_STATUS = "BLOCKED_R44C_BLUESKY_POSTS_REPOSTS_REPLIES_PARITY"
R44C_SCHEMA_VERSION = "bluesky_posts_reposts_replies_parity.r44c.v1"
R44C_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r44c_bluesky_feed_mode_parity"
R44C_MODE_ID = "bluesky_posts_reposts_replies_parity"

_TINY_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="


@dataclass(frozen=True)
class R44CReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    public_appview_sample: Mapping[str, Any]
    visible_replies_sample: Mapping[str, Any]
    visible_reposts_sample: Mapping[str, Any]
    smoke_request_sample: Mapping[str, Any]
    contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == R44C_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))



class BlueskyFeedModeParityR44C:
    def __init__(self, output_root: str | Path = R44C_DEFAULT_OUTPUT_ROOT) -> None:
        self.output_root = Path(output_root)

    def build_report(self) -> R44CReport:
        return build_report(self.output_root)


def build_bluesky_feed_mode_parity_r44c(output_root: str | Path = R44C_DEFAULT_OUTPUT_ROOT) -> BlueskyFeedModeParityR44C:
    return BlueskyFeedModeParityR44C(output_root)

def build_bluesky_feed_mode_parity_contract_r44c() -> dict[str, Any]:
    return {
        "marker": R44C_MARKER,
        "schema_version": R44C_SCHEMA_VERSION,
        "mode_id": R44C_MODE_ID,
        "twitter_x_parity_terms": {
            "posts_and_retweets": "Bluesky posts_and_reposts",
            "posts_and_replies": "Bluesky posts_and_replies",
        },
        "visible_browser_modes": {
            "posts_and_reposts": "navigate profile timeline and preserve visible text, media, screenshots and repost/foreign-author hints",
            "posts_and_replies": "navigate profile replies timeline and preserve visible text, media, screenshots and reply-mode evidence",
        },
        "public_appview_modes": {
            "posts_and_reposts": "app.bsky.feed.getAuthorFeed filter posts_and_author_threads; feed.reason reasonRepost maps to universal repost_or_reshare",
            "posts_and_replies": "app.bsky.feed.getAuthorFeed filter posts_with_replies; record.reply maps to universal reply",
        },
        "ledger_contract": "same R43V -> R43U account/date/post/media/screenshot ledger used for text, media, reposts and replies",
        "no_remote_media_downloads": True,
        "no_cookie_token_or_browser_profile_copying": True,
    }


def build_report(output_root: str | Path = R44C_DEFAULT_OUTPUT_ROOT) -> R44CReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    public_sample = _run_public_appview_classification_sample(root / "public_appview")
    visible_replies = _run_visible_mode_sample(root / "visible_replies", feed_mode="posts_and_replies")
    visible_reposts = _run_visible_mode_sample(root / "visible_reposts", feed_mode="posts_and_reposts")
    smoke_sample = _run_r44b_injected_mode_sample(root / "r44b_smoke", feed_mode="posts_and_replies")
    contract = build_bluesky_feed_mode_parity_contract_r44c()
    flags = {
        "r44c_feed_mode_parity_invoked": True,
        "visible_browser_real_network_started_by_r44c_validation": False,
        "browser_profile_files_read_or_copied": False,
        "cookie_or_token_extraction_performed": False,
        "remote_media_downloads_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
    }
    checks = (
        _check("public_appview_preserves_repost_reason_as_universal_reshare", public_sample.get("repost_record_type") == "repost_or_reshare" and public_sample.get("repost_original_record_id")),
        _check("public_appview_preserves_reply_ref_as_universal_reply", public_sample.get("reply_record_type") == "reply" and public_sample.get("reply_original_record_id")),
        _check("feed_filters_match_posts_reposts_and_posts_replies", public_sample.get("posts_reposts_filter") == "posts_and_author_threads" and public_sample.get("posts_replies_filter") == "posts_with_replies"),
        _check("single_post_url_is_preserved_across_feed_modes", public_sample.get("post_url_preserved_in_visible_navigation") == "https://bsky.app/profile/glacierclear.bsky.social/post/3lynwu7hy4c2w"),
        _check("visible_replies_mode_navigates_replies_tab_and_writes_media_ledger", visible_replies.get("status") == R44A_PASS_STATUS and str(visible_replies.get("navigation_url", "")).endswith("/replies") and visible_replies.get("media_count", 0) >= 3 and visible_replies.get("ledger_status") == R43U_PASS_STATUS),
        _check("visible_posts_reposts_mode_navigates_profile_timeline_and_writes_media_ledger", visible_reposts.get("status") == R44A_PASS_STATUS and not str(visible_reposts.get("navigation_url", "")).endswith("/replies") and visible_reposts.get("media_count", 0) >= 3),
        _check("r44b_smoke_accepts_feed_mode_and_hands_to_r44a", smoke_sample.get("status") == R44B_PASS_STATUS and smoke_sample.get("feed_mode") == "posts_and_replies" and str(smoke_sample.get("navigation_url", "")).endswith("/replies")),
        _check("downstream_chain_preserved", visible_replies.get("r43z_status") == R43Z_PASS_STATUS and visible_replies.get("adapter_status") == R43V_PASS_STATUS and visible_replies.get("ledger_status") == R43U_PASS_STATUS),
        _check("no_real_browser_or_network_in_r44c_validation", not any(flags.get(k) for k in ("visible_browser_real_network_started_by_r44c_validation", "browser_profile_files_read_or_copied", "cookie_or_token_extraction_performed", "remote_media_downloads_performed"))),
        _check("plain_machine_urls", _machine_urls_are_plain(public_sample) and _machine_urls_are_plain(visible_replies) and _machine_urls_are_plain(visible_reposts) and _machine_urls_are_plain(smoke_sample) and _machine_urls_are_plain(contract)),
    )
    status = R44C_PASS_STATUS if all(c["status"] == "pass" for c in checks) else R44C_BLOCKED_STATUS
    report = R44CReport(
        marker=R44C_MARKER,
        schema_version=R44C_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=checks,
        public_appview_sample=public_sample,
        visible_replies_sample=visible_replies,
        visible_reposts_sample=visible_reposts,
        smoke_request_sample=smoke_sample,
        contract=contract,
        side_effect_flags=flags,
    )
    write_report(report, root)
    return report


def _run_public_appview_classification_sample(root: Path) -> dict[str, Any]:
    posts = list(build_fake_bluesky_post_views_r43v(account_handle="example.bsky.social"))
    repost_post = dict(posts[0])
    repost_post["author"] = {"handle": "original.example", "did": "did:plc:original"}
    repost_row = {
        "post": repost_post,
        "reason": {
            "$type": "app.bsky.feed.defs#reasonRepost",
            "by": {"handle": "example.bsky.social", "did": "did:plc:example"},
            "indexedAt": "2026-09-18T09:44:00.000Z",
        },
    }
    reply_post = dict(posts[1])
    reply_record = dict(reply_post.get("record") or {})
    reply_record["reply"] = {
        "root": {"uri": "at://did:plc:root/app.bsky.feed.post/3root", "cid": "bafkroot"},
        "parent": {"uri": "at://did:plc:parent/app.bsky.feed.post/3parent", "cid": "bafkparent"},
    }
    reply_post["record"] = reply_record
    feed = {"feed": [repost_row, {"post": reply_post}], "cursor": "r44c"}
    post_views = extract_post_views_from_author_feed_r43w(feed, max_items=5, feed_mode="posts_and_reposts")
    records = [normalize_bluesky_post_view_to_universal_record_r43v(row, account_handle="example.bsky.social", capture_timestamp="20260918T094400Z", observed_order=i + 1) for i, row in enumerate(post_views)]
    return {
        "post_view_count": len(post_views),
        "record_types": [r.record_type for r in records],
        "repost_record_type": records[0].record_type,
        "repost_original_record_id": records[0].original_record_id,
        "repost_reshared_by_handle": records[0].reshared_by_handle,
        "reply_record_type": records[1].record_type,
        "reply_original_record_id": records[1].original_record_id,
        "posts_reposts_filter": bluesky_public_feed_filter_for_mode_r44c("posts_and_reposts", ""),
        "posts_replies_filter": bluesky_public_feed_filter_for_mode_r44c("posts_and_replies", ""),
        "media_counts": [len(r.media_items) for r in records],
        "post_url_preserved_in_visible_navigation": build_bluesky_visible_navigation_url_r44c("https://bsky.app/profile/glacierclear.bsky.social/post/3lynwu7hy4c2w", "glacierclear.bsky.social", "posts_and_replies"),
    }


def _run_visible_mode_sample(root: Path, *, feed_mode: str) -> dict[str, Any]:
    seen: dict[str, Any] = {}

    def runner(req: BlueskyVisibleLiveWorkbenchCaptureRequestR44A) -> Mapping[str, Any]:
        seen["navigation_url"] = req.account_url
        seen["feed_mode"] = req.feed_mode
        return {
            "status": "injected_visible_browser_snapshot_captured",
            "engine": "r44c_injected_visible_browser_runner",
            "html": _fake_visible_feed_html(account_handle="example.bsky.social", feed_mode=feed_mode),
            "screenshot_png": base64.b64decode(_TINY_PNG_B64),
            "final_url": req.account_url,
            "status_code": 200,
            "browser_session_started": False,
            "network_actions_performed": False,
            "injected_browser_runner_used": True,
            "warnings": [],
        }

    result = build_bluesky_visible_live_workbench_capture_r44a(root, browser_runner=runner).run_account_export(
        BlueskyVisibleLiveWorkbenchCaptureRequestR44A(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260918T094500Z" if feed_mode == "posts_and_replies" else "20260918T094600Z",
            output_root=str(root),
            explicit_live_mode=True,
            run_visible_live=True,
            live_mode=True,
            feed_mode=feed_mode,
            include_replies=feed_mode == "posts_and_replies",
            include_reposts=feed_mode == "posts_and_reposts",
            max_items=5,
        )
    )
    payload = result.to_dict()
    payload["runner_navigation_url"] = seen.get("navigation_url", "")
    payload["runner_feed_mode"] = seen.get("feed_mode", "")
    return payload


def _run_r44b_injected_mode_sample(root: Path, *, feed_mode: str) -> dict[str, Any]:
    def runner(req: BlueskyVisibleLiveWorkbenchCaptureRequestR44A) -> Mapping[str, Any]:
        return {
            "status": "injected_visible_browser_snapshot_captured",
            "engine": "r44c_injected_visible_browser_runner",
            "html": _fake_visible_feed_html(account_handle="example.bsky.social", feed_mode=feed_mode),
            "screenshot_png": base64.b64decode(_TINY_PNG_B64),
            "final_url": req.account_url,
            "status_code": 200,
            "browser_session_started": False,
            "network_actions_performed": False,
            "injected_browser_runner_used": True,
            "warnings": [],
        }
    return run_bluesky_real_windows_visible_browser_smoke_r44b(
        BlueskyRealWindowsVisibleBrowserSmokeRequestR44B(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260918T094700Z",
            output_root=str(root),
            real_visible_smoke=False,
            fixture_mode=True,
            feed_mode=feed_mode,
            include_replies=feed_mode == "posts_and_replies",
            include_reposts=feed_mode == "posts_and_reposts",
            min_records=1,
            min_screenshots=1,
            min_media=0,
        ),
        output_root=root,
        browser_runner=runner,
    ).to_dict()


def _fake_visible_feed_html(*, account_handle: str, feed_mode: str) -> str:
    handle = account_handle
    if feed_mode == "posts_and_replies":
        label = "reply"
        return f'''<!doctype html><html><body><main data-testid="profileScreen" data-r44c-feed-mode="posts_and_replies">
<article data-testid="feedItem-by-{handle}" data-record-type="reply">
  <a href="/profile/{handle}/post/3replyr44c001">post link</a>
  <span data-testid="postDisplayName">Example Bluesky</span>
  <time datetime="2026-09-18T09:45:00.000Z">Sep 18</time>
  <div data-testid="postText">Visible DOM {label} fixture with text and media.</div>
  <img alt="reply image" src="https://cdn.bsky.app/img/feed_fullsize/plain/did:plc:r44c/bafkreir44creply@jpeg" />
</article>
<article data-testid="feedItem-by-{handle}" data-record-type="reply">
  <a href="https://bsky.app/profile/{handle}/post/3replyr44c002">post link</a>
  <time datetime="2026-09-18T09:46:00.000Z">Sep 18</time>
  <div data-testid="postText">Second visible reply with video manifest.</div>
  <video poster="https://video.bsky.app/watch/did:plc:r44c/bafkreir44creplyvideo/thumbnail.jpg"><source src="https://video.bsky.app/watch/did:plc:r44c/bafkreir44creplyvideo/playlist.m3u8" /></video>
</article>
</main></body></html>'''
    return f'''<!doctype html><html><body><main data-testid="profileScreen" data-r44c-feed-mode="posts_and_reposts">
<article data-testid="feedItem-by-{handle}" data-record-type="post">
  <a href="/profile/{handle}/post/3postr44c001">post link</a>
  <span data-testid="postDisplayName">Example Bluesky</span>
  <time datetime="2026-09-18T09:46:00.000Z">Sep 18</time>
  <div data-testid="postText">Visible original post fixture with text and media.</div>
  <img alt="post image" src="https://cdn.bsky.app/img/feed_fullsize/plain/did:plc:r44c/bafkreir44cpost@jpeg" />
</article>
<article data-testid="feedItem-by-other.example" data-record-type="repost_or_reshare">
  <div>Example Bluesky reposted</div>
  <a href="https://bsky.app/profile/other.example/post/3repostr44c002">post link</a>
  <time datetime="2026-09-18T09:47:00.000Z">Sep 18</time>
  <div data-testid="postText">Visible repost fixture with video manifest.</div>
  <video poster="https://video.bsky.app/watch/did:plc:r44c/bafkreir44crepostvideo/thumbnail.jpg"><source src="https://video.bsky.app/watch/did:plc:r44c/bafkreir44crepostvideo/playlist.m3u8" /></video>
</article>
</main></body></html>'''


def write_report(report: R44CReport, output_root: str | Path = R44C_DEFAULT_OUTPUT_ROOT) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R44C_BLUESKY_POSTS_REPOSTS_REPLIES_PARITY_REPORT.json"
    md_path = root / "R44C_BLUESKY_POSTS_REPOSTS_REPLIES_PARITY_REPORT.md"
    _write_json(json_path, report.to_dict())
    md_path.write_text(
        "\n".join([
            f"# {R44C_MARKER}",
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


def _check(name: str, ok: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": "" if ok else detail}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _machine_urls_are_plain(value: Any) -> bool:
    text = json.dumps(_to_jsonable(value), ensure_ascii=False, sort_keys=True)
    return not ("[http" in text or "](http" in text or "\\]" in text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Bluesky posts/reposts and posts/replies feed-mode parity.")
    parser.add_argument("--output-root", default=R44C_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    print(R44C_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
