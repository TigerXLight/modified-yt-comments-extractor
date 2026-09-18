from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

from profile_media_universal_social_account_ledger_contract_r43u import (
    R43U_PASS_STATUS,
    UniversalSocialMediaItemR43U,
    UniversalSocialRecordR43U,
    write_universal_social_account_ledger_r43u,
)

R43V_MARKER = "YTCE_R43V_BLUESKY_VISIBLE_ACCOUNT_ADAPTER"
R43V_PASS_STATUS = "PASS_R43V_BLUESKY_VISIBLE_ACCOUNT_ADAPTER"
R43V_BLOCKED_STATUS = "BLOCKED_R43V_BLUESKY_VISIBLE_ACCOUNT_ADAPTER"
R43V_SCHEMA_VERSION = "bluesky_visible_account_adapter.r43v.v1"
R43V_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43v_bluesky_visible_account_adapter"
R43V_MODE_ID = "bluesky_visible_account_adapter"

BLUESKY_PUBLIC_REFERENCE_PATHS_R43V = (
    "atproto/lexicons/app/bsky/feed/post.json",
    "atproto/lexicons/app/bsky/feed/getAuthorFeed.json",
    "atproto/lexicons/app/bsky/feed/getPosts.json",
    "atproto/lexicons/app/bsky/feed/getPostThread.json",
    "atproto/lexicons/app/bsky/embed/images.json",
    "atproto/lexicons/app/bsky/embed/video.json",
    "atproto/lexicons/app/bsky/embed/external.json",
    "atproto/lexicons/app/bsky/embed/recordWithMedia.json",
    "social-app/src/view/com/posts/PostFeedItem.tsx",
    "social-app/src/view/com/post/Post.tsx",
    "social-app/src/components/Post/Embed/index.tsx",
    "social-app/src/components/Post/Embed/ImageEmbed.tsx",
    "social-app/src/components/Post/Embed/VideoEmbed/index.web.tsx",
    "social-app/bskyweb/templates/post.html",
)


@dataclass(frozen=True)
class BlueskyVisibleAccountAdapterRequestR43V:
    account_url: str = ""
    account_handle: str = ""
    capture_timestamp: str = ""
    output_root: str = R43V_DEFAULT_OUTPUT_ROOT
    fixture_mode: bool = False
    imported_post_views: tuple[Mapping[str, Any], ...] = ()
    initial_records: tuple[Mapping[str, Any], ...] = ()
    static_screenshot_path: str = ""
    include_media: bool = True
    include_static_screenshots: bool = True
    require_screenshot_receipts: bool = True
    explicit_live_mode: bool = False
    run_visible_live: bool = False
    live_mode: bool = False
    max_items: int = 3
    max_scrolls: int = 2

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["imported_post_views"] = [_to_jsonable(item) for item in self.imported_post_views]
        data["initial_records"] = [_to_jsonable(item) for item in self.initial_records]
        return _to_jsonable(data)


@dataclass(frozen=True)
class BlueskyVisibleAccountAdapterResultR43V:
    marker: str
    schema_version: str
    status: str
    account_handle: str
    account_url: str
    capture_timestamp: str
    output_root: str
    receipt_path: str
    ledger_status: str
    account_capture_dir: str = ""
    account_record_path: str = ""
    manifest_path: str = ""
    account_timeline_path: str = ""
    media_index_path: str = ""
    progress_events_path: str = ""
    review_strings_path: str = ""
    record_count: int = 0
    media_count: int = 0
    screenshot_count: int = 0
    date_folders: tuple[str, ...] = ()
    post_folder_count: int = 0
    normalized_records: tuple[Mapping[str, Any], ...] = ()
    side_effect_flags: Mapping[str, bool] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R43V_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43VReport:
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
        return self.status == R43V_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


class BlueskyVisibleAccountAdapterR43V:
    """Map public/visible Bluesky post-view style records into the R43U ledger."""

    def __init__(self, output_root: str | Path = R43V_DEFAULT_OUTPUT_ROOT) -> None:
        self.output_root = Path(output_root)

    def run_account_export(
        self,
        request: BlueskyVisibleAccountAdapterRequestR43V | Mapping[str, Any] | None = None,
        *,
        initial_records: Iterable[Mapping[str, Any]] | None = None,
        imported_post_views: Iterable[Mapping[str, Any]] | None = None,
        **overrides: Any,
    ) -> BlueskyVisibleAccountAdapterResultR43V:
        req = coerce_bluesky_visible_account_adapter_request_r43v(
            request,
            initial_records=tuple(initial_records or ()),
            imported_post_views=tuple(imported_post_views or ()),
            **overrides,
        )
        return run_bluesky_visible_account_adapter_r43v(req, output_root=self.output_root)


def build_bluesky_visible_account_adapter_r43v(output_root: str | Path = R43V_DEFAULT_OUTPUT_ROOT) -> BlueskyVisibleAccountAdapterR43V:
    return BlueskyVisibleAccountAdapterR43V(output_root=output_root)


def build_bluesky_visible_account_adapter_contract_r43v() -> dict[str, Any]:
    return {
        "marker": R43V_MARKER,
        "schema_version": R43V_SCHEMA_VERSION,
        "mode_id": R43V_MODE_ID,
        "method_reused_from_r43t": True,
        "twitter_x_internals_reused": False,
        "live_browser_capture_added": False,
        "network_requests_performed_by_r43v": False,
        "remote_media_downloads_performed_by_r43v": False,
        "accepted_inputs": [
            "imported app.bsky.feed.defs#postView objects",
            "bskyweb/single-post metadata mapped by a caller",
            "future visible-browser observations normalized by a caller",
            "fixture_mode sample records for contract validation",
        ],
        "bluesky_identity_fields": ["did", "handle", "at_uri", "cid", "rkey"],
        "bluesky_embed_types": [
            "app.bsky.embed.images",
            "app.bsky.embed.video",
            "app.bsky.embed.external",
            "app.bsky.embed.record",
            "app.bsky.embed.recordWithMedia",
        ],
        "binding_strategy": [
            "at_uri/rkey/cid where imported public post views provide them",
            "bsky.app profile/post URL where visible page links provide it",
            "DOM proximity for future visible-browser media observations",
            "preserve unbound account-level candidates without fake binding",
        ],
        "repo_reference_paths": list(BLUESKY_PUBLIC_REFERENCE_PATHS_R43V),
    }


def run_bluesky_visible_account_adapter_r43v(
    request: BlueskyVisibleAccountAdapterRequestR43V | Mapping[str, Any] | None = None,
    *,
    output_root: str | Path = R43V_DEFAULT_OUTPUT_ROOT,
) -> BlueskyVisibleAccountAdapterResultR43V:
    req = coerce_bluesky_visible_account_adapter_request_r43v(request)
    root = Path(req.output_root or output_root or R43V_DEFAULT_OUTPUT_ROOT)
    capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
    account_url = _plain_url(req.account_url)
    parsed_url = parse_bluesky_app_url_r43v(account_url)
    handle = _safe_handle(req.account_handle or parsed_url.get("handle") or "example.bsky.social")
    if not account_url:
        account_url = f"https://bsky.app/profile/{handle}"
    run_dir = root / handle / f"bluesky_visible_account_adapter_{capture_ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = run_dir / "r43v_bluesky_visible_account_adapter_receipt.json"

    warnings: list[str] = []
    normalized_records: list[UniversalSocialRecordR43U] = []
    if req.initial_records:
        normalized_records = [_coerce_initial_record(row, account_handle=handle, capture_timestamp=capture_ts) for row in req.initial_records]
    else:
        post_views = list(req.imported_post_views or ())
        if req.fixture_mode and not post_views:
            post_views = list(build_fake_bluesky_post_views_r43v(account_handle=handle))
        limit = max(_safe_int(req.max_items), 0) or len(post_views)
        for index, post_view in enumerate(post_views[:limit], start=1):
            normalized_records.append(
                normalize_bluesky_post_view_to_universal_record_r43v(
                    post_view,
                    account_handle=handle,
                    capture_timestamp=capture_ts,
                    observed_order=index,
                    static_screenshot_path=req.static_screenshot_path if req.include_static_screenshots else "",
                    include_media=req.include_media,
                )
            )

    if not normalized_records:
        warnings.append("No imported Bluesky post views or normalized records were supplied; R43V live browser capture is not implemented in this step.")
        result = BlueskyVisibleAccountAdapterResultR43V(
            marker=R43V_MARKER,
            schema_version=R43V_SCHEMA_VERSION,
            status=R43V_BLOCKED_STATUS,
            account_handle=handle,
            account_url=account_url,
            capture_timestamp=capture_ts,
            output_root=str(root),
            receipt_path=str(receipt_path),
            ledger_status="not_written_no_source_records",
            normalized_records=(),
            side_effect_flags=build_r43v_side_effect_flags(),
            warnings=tuple(warnings),
        )
        _write_json(receipt_path, result.to_dict())
        return result

    ledger = write_universal_social_account_ledger_r43u(
        normalized_records,
        output_root=root,
        platform_id="bluesky",
        account_handle=handle,
        capture_timestamp=capture_ts,
    )
    status = R43V_PASS_STATUS if ledger.status == R43U_PASS_STATUS and ledger.record_count > 0 else R43V_BLOCKED_STATUS
    result = BlueskyVisibleAccountAdapterResultR43V(
        marker=R43V_MARKER,
        schema_version=R43V_SCHEMA_VERSION,
        status=status,
        account_handle=handle,
        account_url=account_url,
        capture_timestamp=capture_ts,
        output_root=str(root),
        receipt_path=str(receipt_path),
        ledger_status=ledger.status,
        account_capture_dir=ledger.account_capture_dir,
        account_record_path=ledger.account_record_path,
        manifest_path=ledger.manifest_path,
        account_timeline_path=ledger.account_timeline_path,
        media_index_path=ledger.media_index_path,
        progress_events_path=ledger.progress_events_path,
        review_strings_path=ledger.review_strings_path,
        record_count=ledger.record_count,
        media_count=ledger.media_count,
        screenshot_count=ledger.screenshot_count,
        date_folders=ledger.date_folders,
        post_folder_count=ledger.post_folder_count,
        normalized_records=tuple(row.to_dict() for row in normalized_records),
        side_effect_flags=build_r43v_side_effect_flags(),
        warnings=tuple(warnings),
    )
    _write_json(receipt_path, result.to_dict())
    return result


def normalize_bluesky_post_view_to_universal_record_r43v(
    post_view: Mapping[str, Any],
    *,
    account_handle: str = "",
    capture_timestamp: str = "",
    observed_order: int = 0,
    static_screenshot_path: str = "",
    include_media: bool = True,
) -> UniversalSocialRecordR43U:
    post = _unwrap_post_view(post_view)
    record = _mapping(post.get("record"))
    author = _mapping(post.get("author"))
    uri = _clean(post.get("uri") or record.get("uri"))
    cid = _clean(post.get("cid"))
    parsed = parse_bluesky_at_uri_r43v(uri)
    rkey = _clean(parsed.get("rkey") or _rkey_from_url(_clean(post.get("source_url"))))
    author_handle = _safe_handle(author.get("handle") or account_handle)
    author_did = _clean(author.get("did") or parsed.get("did"))
    record_id = _safe_record_id(rkey or cid or uri)
    source_url = _plain_url(post.get("source_url") or build_bluesky_post_url_r43v(author_handle or author_did or account_handle, rkey or record_id))
    media_items = (
        _extract_bluesky_embed_media_r43v(_mapping(post.get("embed")), record_id=record_id, source_url=source_url, at_uri=uri)
        if include_media and post.get("embed") else ()
    )
    return UniversalSocialRecordR43U(
        platform_id="bluesky",
        account_handle=_safe_handle(account_handle or author_handle),
        record_id=record_id,
        record_type="post",
        source_url=source_url,
        visible_text=_clean(record.get("text") or post.get("text")),
        visible_timestamp=_clean(record.get("createdAt") or post.get("indexedAt")),
        capture_timestamp=_safe_ts(capture_timestamp),
        author_handle=author_handle,
        author_display_name=_clean(author.get("displayName")),
        static_screenshot_path=_clean(static_screenshot_path),
        media_items=media_items,
        review_strings=(f"bluesky|{author_handle}|{record_id}|{source_url}",),
        observed_order=observed_order,
        platform_specific={"bluesky": {
            "did": author_did, "handle": author_handle, "at_uri": uri, "cid": cid,
            "rkey": rkey, "app_bsky_url": source_url, "indexed_at": _clean(post.get("indexedAt")),
            "reply_count": _safe_int(post.get("replyCount")), "repost_count": _safe_int(post.get("repostCount")),
            "like_count": _safe_int(post.get("likeCount")), "quote_count": _safe_int(post.get("quoteCount")),
            "embed_type": _embed_type(_mapping(post.get("embed"))),
        }},
    )


def _extract_bluesky_embed_media_r43v(embed: Mapping[str, Any], *, record_id: str, source_url: str, at_uri: str = "") -> tuple[UniversalSocialMediaItemR43U, ...]:
    embed_type = _embed_type(embed)
    media: list[UniversalSocialMediaItemR43U] = []
    if not embed:
        return ()
    if "recordWithMedia" in embed_type:
        return _extract_bluesky_embed_media_r43v(_mapping(embed.get("media")), record_id=record_id, source_url=source_url, at_uri=at_uri)
    if "images" in embed_type:
        for index, image in enumerate(_sequence(embed.get("images")), start=1):
            item = _mapping(image)
            media_url = _plain_url(item.get("fullsize") or item.get("thumb"))
            if media_url:
                media.append(_media_item(
                    record_id, source_url, media_url, "image", "bluesky_post_view_embed_image",
                    "bluesky_app_bsky_embed_images_view", filename=f"{record_id}_image_{index}.jpg",
                    mime_type=_mime_from_url(media_url) or "image/jpeg",
                    platform_specific={"bluesky": {"alt": _clean(item.get("alt")), "thumb": _plain_url(item.get("thumb")), "at_uri": at_uri}},
                ))
    elif "video" in embed_type:
        playlist = _plain_url(embed.get("playlist"))
        thumbnail = _plain_url(embed.get("thumbnail"))
        if playlist:
            media.append(_media_item(
                record_id, source_url, playlist, "manifest", "bluesky_post_view_embed_video_playlist",
                "bluesky_app_bsky_embed_video_view", filename=f"{record_id}_video_playlist.m3u8",
                mime_type="application/vnd.apple.mpegurl", playlist_manifest_url=playlist,
                platform_specific={"bluesky": {"cid": _clean(embed.get("cid")), "alt": _clean(embed.get("alt")), "at_uri": at_uri}},
            ))
        if thumbnail:
            media.append(_media_item(
                record_id, source_url, thumbnail, "image", "bluesky_post_view_embed_video_thumbnail",
                "bluesky_app_bsky_embed_video_view", filename=f"{record_id}_video_thumbnail.jpg",
                mime_type=_mime_from_url(thumbnail) or "image/jpeg", playlist_manifest_url=playlist,
                platform_specific={"bluesky": {"cid": _clean(embed.get("cid")), "alt": _clean(embed.get("alt")), "at_uri": at_uri}},
            ))
    elif "external" in embed_type:
        external = _mapping(embed.get("external"))
        media_url = _plain_url(external.get("thumb") or external.get("uri"))
        if media_url:
            media.append(_media_item(
                record_id, source_url, media_url, "external", "bluesky_post_view_embed_external",
                "bluesky_app_bsky_embed_external_view", filename=f"{record_id}_external.url.txt",
                platform_specific={"bluesky": {"uri": _plain_url(external.get("uri")), "title": _clean(external.get("title")), "description": _clean(external.get("description")), "at_uri": at_uri}},
            ))
    return tuple(media)


def _media_item(record_id: str, source_url: str, media_url: str, media_class: str, binding_reason: str, observation_kind: str, *, filename: str = "", mime_type: str = "", playlist_manifest_url: str = "", platform_specific: Mapping[str, Any] | None = None) -> UniversalSocialMediaItemR43U:
    return UniversalSocialMediaItemR43U(
        media_id=_safe_media_id(f"{record_id}_{media_class}_{media_url}"),
        media_class=media_class,
        source_url=source_url,
        media_url=media_url,
        filename=filename or _filename_from_url(media_url),
        mime_type=mime_type,
        byte_status="metadata_only_remote_media_not_downloaded",
        provenance=f"R43V {observation_kind}",
        warning=f"metadata-only Bluesky {media_class} receipt; R43V did not download remote media",
        bound_to_record_id=record_id,
        bound_to_source_url=source_url,
        binding_status="bound_to_post",
        binding_reason=binding_reason,
        source_observation_kind=observation_kind,
        source_observation_marker="R43V",
        metadata_only_remote_media_not_downloaded=True,
        playlist_manifest_url=playlist_manifest_url,
        platform_specific=dict(platform_specific or {}),
    )


def build_fake_bluesky_post_views_r43v(account_handle: str = "example.bsky.social") -> tuple[dict[str, Any], ...]:
    handle = _safe_handle(account_handle or "example.bsky.social")
    did = "did:plc:r43vexample"
    return (
        {
            "uri": f"at://{did}/app.bsky.feed.post/3lxyzimagepost",
            "cid": "bafyreir43vimagecid",
            "author": {"did": did, "handle": handle, "displayName": "Example Bluesky"},
            "record": {"$type": "app.bsky.feed.post", "text": "Bluesky image fixture for universal ledger binding.", "createdAt": "2026-09-18T05:05:00.000Z"},
            "indexedAt": "2026-09-18T05:05:02.000Z",
            "embed": {"$type": "app.bsky.embed.images#view", "images": [{"thumb": "https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:r43vexample/bafkreir43vthumb@jpeg", "fullsize": "https://cdn.bsky.app/img/feed_fullsize/plain/did:plc:r43vexample/bafkreir43vfull@jpeg", "alt": "fixture image alt text"}]},
            "replyCount": 1, "repostCount": 2, "likeCount": 3, "quoteCount": 0,
        },
        {
            "uri": f"at://{did}/app.bsky.feed.post/3lxyzvideopost",
            "cid": "bafyreir43vvideocid",
            "author": {"did": did, "handle": handle, "displayName": "Example Bluesky"},
            "record": {"$type": "app.bsky.feed.post", "text": "Bluesky video fixture for manifest and thumbnail receipts.", "createdAt": "2026-09-18T05:06:00.000Z"},
            "indexedAt": "2026-09-18T05:06:02.000Z",
            "embed": {"$type": "app.bsky.embed.recordWithMedia#view", "media": {"$type": "app.bsky.embed.video#view", "cid": "bafkreir43vvideoblob", "playlist": "https://video.bsky.app/watch/did:plc:r43vexample/bafkreir43vvideoblob/playlist.m3u8", "thumbnail": "https://video.bsky.app/watch/did:plc:r43vexample/bafkreir43vvideoblob/thumbnail.jpg", "alt": "fixture video alt text"}, "record": {"$type": "app.bsky.embed.record#view", "uri": f"at://{did}/app.bsky.feed.post/3lxyzquoted"}},
            "replyCount": 0, "repostCount": 0, "likeCount": 1, "quoteCount": 1,
        },
    )


def parse_bluesky_app_url_r43v(value: str) -> dict[str, str]:
    parsed = urlsplit(_plain_url(value))
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]
    result = {"host": host, "handle": "", "rkey": "", "url_kind": "unknown"}
    if host in {"bsky.app", "staging.bsky.app"} and len(parts) >= 2 and parts[0] == "profile":
        result.update({"handle": _safe_handle(parts[1]), "url_kind": "account"})
        if len(parts) >= 4 and parts[2] == "post":
            result.update({"rkey": _safe_record_id(parts[3]), "url_kind": "post"})
    return result


def parse_bluesky_at_uri_r43v(value: str) -> dict[str, str]:
    result = {"did": "", "collection": "", "rkey": ""}
    match = re.match(r"^at://([^/]+)/([^/]+)/([^/?#]+)", _clean(value))
    if match:
        result.update({"did": match.group(1), "collection": match.group(2), "rkey": match.group(3)})
    return result


def build_bluesky_post_url_r43v(handle_or_did: str, rkey: str) -> str:
    return f"https://bsky.app/profile/{_safe_handle(handle_or_did or 'unknown_account')}/post/{_safe_record_id(rkey or 'unknown_post')}"


def coerce_bluesky_visible_account_adapter_request_r43v(request: BlueskyVisibleAccountAdapterRequestR43V | Mapping[str, Any] | None = None, **overrides: Any) -> BlueskyVisibleAccountAdapterRequestR43V:
    data = request.to_dict() if isinstance(request, BlueskyVisibleAccountAdapterRequestR43V) else dict(request or {})
    for key, value in overrides.items():
        if value not in (None, ""):
            data[key] = value
    return BlueskyVisibleAccountAdapterRequestR43V(
        account_url=_plain_url(data.get("account_url") or ""), account_handle=_safe_handle(data.get("account_handle") or ""), capture_timestamp=_safe_ts(data.get("capture_timestamp") or ""), output_root=_clean(data.get("output_root") or R43V_DEFAULT_OUTPUT_ROOT), fixture_mode=_to_bool(data.get("fixture_mode"), False), imported_post_views=tuple(_mapping(item) for item in data.get("imported_post_views") or ()), initial_records=tuple(_mapping(item) for item in data.get("initial_records") or ()), static_screenshot_path=_clean(data.get("static_screenshot_path") or ""), include_media=_to_bool(data.get("include_media"), True), include_static_screenshots=_to_bool(data.get("include_static_screenshots"), True), require_screenshot_receipts=_to_bool(data.get("require_screenshot_receipts"), True), explicit_live_mode=_to_bool(data.get("explicit_live_mode"), False), run_visible_live=_to_bool(data.get("run_visible_live"), False), live_mode=_to_bool(data.get("live_mode"), False), max_items=_safe_int(data.get("max_items"), 3), max_scrolls=_safe_int(data.get("max_scrolls"), 2),
    )


def build_r43v_side_effect_flags() -> dict[str, bool]:
    return {"bluesky_adapter_invoked": True, "r43u_universal_ledger_writer_used": True, "twitter_x_code_path_reused": False, "twitter_x_internals_assumed": False, "network_actions_performed": False, "browser_session_started": False, "webview2_session_started_by_r43v": False, "webview2_internals_copied": False, "hidden_platform_api_scraping_performed": False, "cookie_or_token_extraction_performed": False, "login_automation_performed": False, "captcha_or_challenge_bypass_performed": False, "remote_media_downloads_performed": False, "source_role_checks_performed": False, "review_window_dependency_invoked": False}


def build_report(output_root: str | Path = R43V_DEFAULT_OUTPUT_ROOT) -> R43VReport:
    root = Path(output_root); root.mkdir(parents=True, exist_ok=True)
    result = build_bluesky_visible_account_adapter_r43v(root / "sample").run_account_export(BlueskyVisibleAccountAdapterRequestR43V(account_url="https://bsky.app/profile/example.bsky.social", account_handle="example.bsky.social", capture_timestamp="20260918T061000Z", output_root=str(root / "sample"), fixture_mode=True, max_items=5))
    payload = result.to_dict(); contract = build_bluesky_visible_account_adapter_contract_r43v(); flags = build_r43v_side_effect_flags(); media_index = _read_json(result.media_index_path, default=[]); first = (payload.get("normalized_records") or [{}])[0]; bsky = _mapping(_mapping(first.get("platform_specific")).get("bluesky"))
    checks = (
        _check("adapter_passes_fixture_without_network", result.status == R43V_PASS_STATUS and flags["network_actions_performed"] is False),
        _check("uses_r43u_universal_ledger_writer", result.ledger_status == R43U_PASS_STATUS and Path(result.account_capture_dir).is_dir()),
        _check("bluesky_identity_stays_nested", all(key in bsky for key in ("did", "at_uri", "cid", "rkey"))),
        _check("bsky_app_urls_are_plain", _machine_urls_are_plain(payload) and _machine_urls_are_plain(contract)),
        _check("images_video_and_record_with_media_are_mapped", result.media_count >= 3 and any(row.get("media_class") == "manifest" for row in media_index)),
        _check("media_receipts_are_metadata_only", all(row.get("metadata_only_remote_media_not_downloaded") is True and row.get("copied_local_bytes") is False for row in media_index)),
        _check("primary_ledger_files_written", all(Path(path).is_file() for path in (result.account_record_path, result.manifest_path, result.account_timeline_path, result.media_index_path, result.progress_events_path, result.review_strings_path))),
        _check("no_twitter_x_host_assumptions_in_bluesky_output", "pbs.twimg.com" not in json.dumps(payload) and "video.twimg.com" not in json.dumps(payload)),
        _check("repo_reference_paths_recorded", "atproto/lexicons/app/bsky/feed/getAuthorFeed.json" in contract["repo_reference_paths"]),
    )
    status = R43V_PASS_STATUS if all(c["status"] == "pass" for c in checks) else R43V_BLOCKED_STATUS
    report = R43VReport(R43V_MARKER, R43V_SCHEMA_VERSION, datetime.now(timezone.utc).isoformat(), status, checks, payload, contract, flags)
    write_report(report, root)
    return report


def write_report(report: R43VReport, output_root: str | Path = R43V_DEFAULT_OUTPUT_ROOT) -> tuple[Path, Path]:
    root = Path(output_root); root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R43V_BLUESKY_VISIBLE_ACCOUNT_ADAPTER_REPORT.json"; md_path = root / "R43V_BLUESKY_VISIBLE_ACCOUNT_ADAPTER_REPORT.md"
    _write_json(json_path, report.to_dict())
    md_path.write_text("\n".join([f"# {R43V_MARKER}", "", f"- Status: `{report.status}`", f"- Schema: `{report.schema_version}`", f"- Generated: `{report.generated_at}`", "", "## Checks", *[f"- `{c.get('status')}` {c.get('name')}: {c.get('detail') or ''}".rstrip() for c in report.checks]]).rstrip() + "\n", encoding="utf-8")
    return json_path, md_path


def _coerce_initial_record(row: Mapping[str, Any], *, account_handle: str, capture_timestamp: str) -> UniversalSocialRecordR43U:
    media_items = tuple(item if isinstance(item, UniversalSocialMediaItemR43U) else UniversalSocialMediaItemR43U(**{k: v for k, v in _mapping(item).items() if k in UniversalSocialMediaItemR43U.__dataclass_fields__}) for item in row.get("media_items") or ())
    allowed = {k: v for k, v in _mapping(row).items() if k in UniversalSocialRecordR43U.__dataclass_fields__ and k != "media_items"}
    allowed.setdefault("platform_id", "bluesky"); allowed.setdefault("account_handle", account_handle); allowed.setdefault("capture_timestamp", capture_timestamp); allowed["media_items"] = media_items
    return UniversalSocialRecordR43U(**allowed)


def _unwrap_post_view(value: Mapping[str, Any]) -> Mapping[str, Any]:
    data = _mapping(value)
    return _mapping(data.get("post")) if isinstance(data.get("post"), Mapping) else data


def _embed_type(embed: Mapping[str, Any]) -> str:
    return _clean(embed.get("$type") or embed.get("py_type") or embed.get("type"))


def _rkey_from_url(value: str) -> str:
    return parse_bluesky_app_url_r43v(value).get("rkey", "")


def _plain_url(value: Any) -> str:
    text = _clean(value).strip("<>").replace("\\_", "_").replace("\\/", "/")
    md = re.match(r"^\[[^\]]+\]\((https?://[^)]+)\)$", text)
    return md.group(1) if md else text


def _safe_handle(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]+", "_", _clean(value).strip().lstrip("@")).strip("._-") or "unknown_account"


def _safe_record_id(value: Any) -> str:
    text = _clean(value)
    if text.startswith("at://"):
        text = parse_bluesky_at_uri_r43v(text).get("rkey") or text
    return re.sub(r"[^A-Za-z0-9_.:-]+", "_", text).strip("._-") or "unknown_record"


def _safe_media_id(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]+", "_", re.sub(r"^https?://", "", _clean(value))).strip("._-")[:180] or "unknown_media"


def _safe_ts(value: Any) -> str:
    return re.sub(r"[^0-9TZ]", "", _clean(value).replace(":", "").replace("-", ""))


def _safe_int(value: Any, default: int = 0) -> int:
    try: return int(value or 0)
    except Exception: return default


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None: return default
    if isinstance(value, bool): return value
    return _clean(value).lower() in {"1", "true", "yes", "y", "on"}


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _filename_from_url(url: str) -> str:
    name = (urlsplit(_plain_url(url)).path.rsplit("/", 1)[-1] or "").split("?", 1)[0]
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._-")


def _mime_from_url(url: str) -> str:
    lower = _plain_url(url).lower()
    if lower.endswith(".m3u8"): return "application/vnd.apple.mpegurl"
    if lower.endswith(".mp4"): return "video/mp4"
    if lower.endswith(".png") or "@png" in lower: return "image/png"
    if lower.endswith(".webp") or "@webp" in lower: return "image/webp"
    if lower.endswith(".gif") or "@gif" in lower: return "image/gif"
    if lower.endswith(".jpg") or lower.endswith(".jpeg") or "@jpeg" in lower or "@jpg" in lower: return "image/jpeg"
    return ""


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> tuple[Any, ...]:
    return tuple(value) if isinstance(value, (list, tuple)) else ()


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Path): return str(value)
    if hasattr(value, "to_dict"): return value.to_dict()
    if isinstance(value, Mapping): return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)): return [_to_jsonable(v) for v in value]
    return value


def _write_json(path: str | Path, payload: Any) -> None:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(_to_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: str | Path, *, default: Any) -> Any:
    try: return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception: return default


def _machine_urls_are_plain(value: Any, key: str = "") -> bool:
    if isinstance(value, Mapping): return all(_machine_urls_are_plain(child, str(child_key)) for child_key, child in value.items())
    if isinstance(value, (list, tuple, set)): return all(_machine_urls_are_plain(child, key) for child in value)
    if key.endswith("url") or key.endswith("_path") or key in {"account_url", "source_url", "media_url", "playlist_manifest_url"}:
        text = _clean(value); return not text.startswith("[") and "](" not in text and "]\\(" not in text
    return True


def _check(name: str, ok: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": detail}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R43V Bluesky visible/public account adapter report")
    parser.add_argument("--output-root", default=R43V_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    print(R43V_MARKER); print(report.status); print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
