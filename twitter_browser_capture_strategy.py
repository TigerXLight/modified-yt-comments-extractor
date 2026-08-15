from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from twitter_route_strategy import (
    LIST_WORKAROUND_NOT_GUARANTEED,
    NO_FULL_CLAIM_WITHOUT_BOUNDARY,
    RECORD_CURSOR_BOUNDARY,
    STOP_WHEN_NO_NEXT_PAGE,
    classify_twitter_route,
)


TWITTER_BROWSER_CAPTURE_SCHEMA_VERSION = "twitter_browser_capture_strategy.v70"
CAPTURE_MEDIUM_BROWSER_SESSION_NETWORK = "browser_session_network_responses"
CAPTURE_MEDIUM_RENDERED_DOM = "rendered_dom_and_screenshot"
CAPTURE_MEDIUM_SHARED_MEDIA_BACKEND = "shared_media_backend"

DEFAULT_BROWSER_ARTIFACTS = (
    "browser_session_manifest.json",
    "network_events.jsonl",
    "api_pages.jsonl",
    "cursor_boundaries.json",
    "media_inventory.json",
    "rendered_dom_snapshot.html",
    "screenshot.png",
)

STATUS_QUERY_CANDIDATES = ("TweetDetail", "TweetResultByRestId", "TweetResultsByRestIds")
USER_TIMELINE_QUERY_CANDIDATES = ("UserTweets", "UserTweetsAndReplies", "UserMedia")
LIST_QUERY_CANDIDATES = ("ListLatestTweetsTimeline", "ListTimeline", "ListTweets")
BOOKMARK_QUERY_CANDIDATES = ("Bookmarks", "BookmarkTimeline")
LIKES_QUERY_CANDIDATES = ("Favorites", "Likes", "UserLikes")
ARTICLE_QUERY_CANDIDATES = ("Article", "ArticleByRestId", "TweetDetail")


@dataclass(frozen=True)
class TwitterBrowserSessionConfig:
    profile_label: str
    browser_engine: str = "chromium"
    user_data_dir: str = ""
    isolated_profile_required: bool = True
    separate_test_account_recommended: bool = True
    logged_in_session_required: bool = True
    reuse_existing_profile: bool = False
    capture_devtools_network: bool = True
    capture_dom_snapshot: bool = True
    capture_screenshot: bool = True
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterBrowserCaptureStep:
    order: int
    name: str
    capture_medium: str
    query_candidates: tuple[str, ...] = ()
    output_artifacts: tuple[str, ...] = ()
    completion_boundary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterBrowserCapturePlan:
    schema_version: str
    source_url: str
    canonical_url: str
    route_kind: str
    capture_goal: str
    browser_session: TwitterBrowserSessionConfig
    steps: tuple[TwitterBrowserCaptureStep, ...]
    list_workaround_url: str = ""
    list_workaround_guarantees_full_export: bool = False
    completion_policy: str = ""
    evidence_claim_policy: str = ""
    constraints: tuple[str, ...] = ()
    rxliuli_notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterNetworkPageBoundary:
    query_name: str
    source_url: str
    page_number: int
    returned_items_count: int
    cursor_in: str = ""
    cursor_out: str = ""
    next_page_requested: bool = False
    next_page_returned_data: bool = False
    rate_limited: bool = False
    http_status: int = 0
    stop_reason: str = ""
    completeness_state: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def unwrap_source_url(source_url: str) -> str:
    raw = str(source_url or "").strip()
    markdown = re.match(r"^\[([^\]]+)\]\((https?://[^)]+)\)$", raw)
    if markdown:
        return markdown.group(2).strip()
    angle = re.match(r"^<((?:https?://|x\.com/|twitter\.com/)[^>]+)>$", raw, flags=re.I)
    if angle:
        return angle.group(1).strip()
    return raw


def canonicalize_browser_capture_url(source_url: str) -> str:
    raw = unwrap_source_url(source_url)
    if raw and not re.match(r"^[a-z]+://", raw, flags=re.I):
        raw = "https://" + raw
    parsed = urlsplit(raw)
    host = parsed.netloc.lower().removeprefix("www.")
    path = re.sub(r"/+", "/", parsed.path or "/").rstrip("/") or "/"
    return f"https://{host}{path}"


def build_twitter_browser_session_config(
    *,
    profile_label: str = "ytce_twitter_isolated_test_profile",
    browser_engine: str = "chromium",
    user_data_dir: str | Path = "",
    reuse_existing_profile: bool = False,
) -> TwitterBrowserSessionConfig:
    return TwitterBrowserSessionConfig(
        profile_label=profile_label,
        browser_engine=browser_engine,
        user_data_dir=str(user_data_dir or ""),
        reuse_existing_profile=bool(reuse_existing_profile),
        isolated_profile_required=not bool(reuse_existing_profile),
        notes=(
            "Use a separate test account/profile for implementation smoke tests.",
            "Browser-session capture observes the logged-in browser's own network responses; it is not the paid public X API route.",
            "Do not claim full timeline completion without a cursor/no-next-page boundary or known total.",
        ),
    )


def _step(order: int, name: str, medium: str, queries: Sequence[str] = (), artifacts: Sequence[str] = DEFAULT_BROWSER_ARTIFACTS, boundary: str = "") -> TwitterBrowserCaptureStep:
    return TwitterBrowserCaptureStep(
        order=order,
        name=name,
        capture_medium=medium,
        query_candidates=tuple(queries),
        output_artifacts=tuple(artifacts),
        completion_boundary=boundary,
    )


def build_twitter_browser_capture_plan(
    source_url: str,
    *,
    capture_goal: str = "",
    list_workaround_url: str = "",
    session_config: TwitterBrowserSessionConfig | None = None,
) -> TwitterBrowserCapturePlan:
    canonical = canonicalize_browser_capture_url(source_url)
    route_kind = classify_twitter_route(canonical, capture_goal=capture_goal)
    session = session_config or build_twitter_browser_session_config()
    common_constraints = (
        STOP_WHEN_NO_NEXT_PAGE,
        RECORD_CURSOR_BOUNDARY,
        NO_FULL_CLAIM_WITHOUT_BOUNDARY,
    )
    rx_notes = (
        "rxliuli: exporting tweets from a specified user is strict/rate-limited.",
        "rxliuli: lists can be used as a workaround, but full export is not guaranteed.",
        "rxliuli: if the browser-visible Twitter API returns no next page data, record that boundary and stop/resume later.",
        "rxliuli: use an isolated/separate test account to reduce ban risk during capture experiments.",
    )

    if route_kind == "single_status_media":
        steps = (
            _step(1, "load_status_page", CAPTURE_MEDIUM_BROWSER_SESSION_NETWORK, STATUS_QUERY_CANDIDATES, boundary="TweetDetail response captured or page error recorded"),
            _step(2, "extract_media_entities", CAPTURE_MEDIUM_BROWSER_SESSION_NETWORK, ("media_url_https", "video_info", "variants"), artifacts=("media_inventory.json", "api_pages.jsonl")),
            _step(3, "download_public_media", CAPTURE_MEDIUM_SHARED_MEDIA_BACKEND, (), artifacts=("download_manifest.json", "media_files"), boundary="files produced or explicit reviewed no-media state"),
            _step(4, "render_review_artifacts", CAPTURE_MEDIUM_RENDERED_DOM, (), artifacts=("rendered_dom_snapshot.html", "screenshot.png")),
        )
        return TwitterBrowserCapturePlan(
            TWITTER_BROWSER_CAPTURE_SCHEMA_VERSION,
            source_url,
            canonical,
            route_kind,
            capture_goal or "media",
            session,
            steps,
            completion_policy="complete_when_status_response_and_media_files_or_no_media_boundary_are_recorded",
            evidence_claim_policy="claim completed only when files are produced or explicit reviewed no-media state is recorded",
            constraints=(RECORD_CURSOR_BOUNDARY,),
            rxliuli_notes=rx_notes,
        )

    if route_kind in {"user_timeline_strict_limited", "user_media_timeline_strict_limited"}:
        queries = USER_TIMELINE_QUERY_CANDIDATES if route_kind == "user_timeline_strict_limited" else ("UserMedia",)
        steps = (
            _step(1, "load_user_timeline_or_media_tab", CAPTURE_MEDIUM_BROWSER_SESSION_NETWORK, queries, boundary="first API page captured or blocked/rate-limited"),
            _step(2, "page_until_boundary", CAPTURE_MEDIUM_BROWSER_SESSION_NETWORK, queries, artifacts=("api_pages.jsonl", "cursor_boundaries.json"), boundary="no next page data, rate limit, operator stop, or known total"),
            _step(3, "optional_list_workaround", CAPTURE_MEDIUM_BROWSER_SESSION_NETWORK, LIST_QUERY_CANDIDATES, artifacts=("list_api_pages.jsonl", "cursor_boundaries.json"), boundary="list workaround boundary recorded"),
            _step(4, "send_discovered_media_to_backend", CAPTURE_MEDIUM_SHARED_MEDIA_BACKEND, (), artifacts=("media_inventory.json", "download_manifest.json", "media_files")),
        )
        return TwitterBrowserCapturePlan(
            TWITTER_BROWSER_CAPTURE_SCHEMA_VERSION,
            source_url,
            canonical,
            route_kind,
            capture_goal or "user_timeline",
            session,
            steps,
            list_workaround_url=canonicalize_browser_capture_url(list_workaround_url) if list_workaround_url else "",
            list_workaround_guarantees_full_export=False,
            completion_policy="partial_until_known_total_or_explicit_no_next_page_boundary",
            evidence_claim_policy="do not claim full user export merely because a user route or list workaround stopped",
            constraints=common_constraints + (LIST_WORKAROUND_NOT_GUARANTEED,),
            rxliuli_notes=rx_notes,
        )

    if route_kind == "list_timeline_workaround":
        steps = (
            _step(1, "load_list_timeline", CAPTURE_MEDIUM_BROWSER_SESSION_NETWORK, LIST_QUERY_CANDIDATES, boundary="list first page captured or blocked/rate-limited"),
            _step(2, "page_list_until_boundary", CAPTURE_MEDIUM_BROWSER_SESSION_NETWORK, LIST_QUERY_CANDIDATES, artifacts=("list_api_pages.jsonl", "cursor_boundaries.json"), boundary="no next page data, rate limit, operator stop, or known total"),
            _step(3, "send_discovered_media_to_backend", CAPTURE_MEDIUM_SHARED_MEDIA_BACKEND, (), artifacts=("media_inventory.json", "download_manifest.json", "media_files")),
        )
        return TwitterBrowserCapturePlan(
            TWITTER_BROWSER_CAPTURE_SCHEMA_VERSION,
            source_url,
            canonical,
            route_kind,
            capture_goal or "list_timeline",
            session,
            steps,
            list_workaround_url=canonical,
            list_workaround_guarantees_full_export=False,
            completion_policy="complete_or_partial_based_on_recorded_cursor_boundary",
            evidence_claim_policy="list capture can be complete only for the list route boundary, not guaranteed full user history",
            constraints=common_constraints + (LIST_WORKAROUND_NOT_GUARANTEED,),
            rxliuli_notes=rx_notes,
        )

    if route_kind in {"bookmarks_browser_export", "likes_browser_export"}:
        queries = BOOKMARK_QUERY_CANDIDATES if route_kind == "bookmarks_browser_export" else LIKES_QUERY_CANDIDATES
        steps = (
            _step(1, "load_authenticated_collection", CAPTURE_MEDIUM_BROWSER_SESSION_NETWORK, queries, boundary="authenticated first page captured or blocked/rate-limited"),
            _step(2, "page_collection_until_boundary", CAPTURE_MEDIUM_BROWSER_SESSION_NETWORK, queries, artifacts=("api_pages.jsonl", "cursor_boundaries.json"), boundary="no next page data, rate limit, operator stop, or known total"),
            _step(3, "import_or_export_records", "local_export_import", (), artifacts=("records.jsonl", "source_hashes.json")),
        )
        return TwitterBrowserCapturePlan(
            TWITTER_BROWSER_CAPTURE_SCHEMA_VERSION,
            source_url,
            canonical,
            route_kind,
            capture_goal or route_kind,
            session,
            steps,
            completion_policy="complete_or_partial_based_on_authenticated_session_cursor_boundary",
            evidence_claim_policy="completion applies only to the recorded authenticated account/session boundary",
            constraints=common_constraints,
            rxliuli_notes=rx_notes,
        )

    if route_kind == "article_export_render":
        steps = (
            _step(1, "load_article_route", CAPTURE_MEDIUM_BROWSER_SESSION_NETWORK, ARTICLE_QUERY_CANDIDATES, boundary="article API/page response captured"),
            _step(2, "extract_article_content", CAPTURE_MEDIUM_RENDERED_DOM, (), artifacts=("article.json", "article.html")),
            _step(3, "render_article_outputs", CAPTURE_MEDIUM_RENDERED_DOM, (), artifacts=("article.pdf", "screenshot.png")),
        )
        return TwitterBrowserCapturePlan(
            TWITTER_BROWSER_CAPTURE_SCHEMA_VERSION,
            source_url,
            canonical,
            route_kind,
            capture_goal or "article",
            session,
            steps,
            completion_policy="complete_when_article_text_and_rendered_artifacts_are_recorded",
            evidence_claim_policy="completed when extracted text and rendered artifact are produced",
            constraints=(RECORD_CURSOR_BOUNDARY,),
            rxliuli_notes=rx_notes,
        )

    return TwitterBrowserCapturePlan(
        TWITTER_BROWSER_CAPTURE_SCHEMA_VERSION,
        source_url,
        canonical,
        route_kind,
        capture_goal or "unknown",
        session,
        (_step(1, "operator_route_review", "operator_review", (), artifacts=("route_review.json",), boundary="operator chooses a supported route"),),
        completion_policy="not_started_until_route_selected",
        evidence_claim_policy="no completion claim for unknown route",
        constraints=(RECORD_CURSOR_BOUNDARY,),
        rxliuli_notes=rx_notes,
    )


def record_browser_network_page_boundary(
    *,
    query_name: str,
    source_url: str,
    page_number: int,
    returned_items_count: int,
    cursor_in: str = "",
    cursor_out: str = "",
    next_page_requested: bool = False,
    next_page_returned_data: bool = False,
    rate_limited: bool = False,
    http_status: int = 0,
) -> TwitterNetworkPageBoundary:
    if rate_limited or http_status in {429, 403}:
        stop_reason = "rate_limited_or_blocked"
        completeness_state = "partial_rate_limited"
    elif next_page_requested and not next_page_returned_data:
        stop_reason = "next_page_requested_but_no_data_returned"
        completeness_state = "partial_api_boundary"
    elif cursor_out and next_page_returned_data:
        stop_reason = "next_page_available"
        completeness_state = "in_progress"
    elif not cursor_out:
        stop_reason = "no_next_cursor"
        completeness_state = "complete_if_known_total_else_partial_boundary"
    else:
        stop_reason = "operator_boundary"
        completeness_state = "partial_operator_boundary"

    return TwitterNetworkPageBoundary(
        query_name=query_name,
        source_url=source_url,
        page_number=int(page_number),
        returned_items_count=int(returned_items_count),
        cursor_in=str(cursor_in or ""),
        cursor_out=str(cursor_out or ""),
        next_page_requested=bool(next_page_requested),
        next_page_returned_data=bool(next_page_returned_data),
        rate_limited=bool(rate_limited),
        http_status=int(http_status or 0),
        stop_reason=stop_reason,
        completeness_state=completeness_state,
    )


def should_continue_paging(boundary: TwitterNetworkPageBoundary) -> bool:
    return boundary.completeness_state == "in_progress"


def write_twitter_browser_capture_plan(path: str | Path, plan: TwitterBrowserCapturePlan) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return output
