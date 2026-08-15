from __future__ import annotations
import json, re
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit
from twitter_media_backend import TWITTER_MEDIA_BACKEND_PROFILE_ID, build_twitter_media_backend_plan

SCHEMA_VERSION = "twitter_route_strategy.v69"
STRICT_USER_TWEETS_RATE_LIMIT = "strict_user_tweets_rate_limit"
LIST_WORKAROUND_NOT_GUARANTEED = "list_workaround_not_guaranteed_complete"
STOP_WHEN_NO_NEXT_PAGE = "stop_when_api_returns_no_next_page_data"
ISOLATE_TEST_ACCOUNT = "isolate_test_account_recommended"
RECORD_CURSOR_BOUNDARY = "record_cursor_and_page_boundary"
NO_FULL_CLAIM_WITHOUT_BOUNDARY = "no_full_completeness_claim_without_boundary_or_known_total"

@dataclass(frozen=True)
class TwitterRouteAction:
    order: int
    component: str
    action: str
    reason: str = ""

@dataclass(frozen=True)
class TwitterRouteStrategy:
    schema_version: str
    route_kind: str
    source_url: str
    canonical_url: str
    source_id: str
    capture_goal: str
    primary_route: str
    fallback_routes: tuple[str, ...]
    actions: tuple[TwitterRouteAction, ...]
    constraints: tuple[str, ...]
    completion_policy: str
    evidence_completion_claim_policy: str
    notes: tuple[str, ...] = ()
    def to_dict(self) -> dict[str, Any]:
        return _val(self)

@dataclass(frozen=True)
class TwitterPaginationBoundary:
    route_kind: str
    source_url: str
    page_number: int
    returned_items_count: int
    next_cursor: str = ""
    api_returned_next_page_data: bool = False
    rate_limited: bool = False
    stopped_reason: str = ""
    completeness_state: str = "unknown"
    def to_dict(self) -> dict[str, Any]:
        return _val(self)

def _val(v: Any) -> Any:
    if is_dataclass(v):
        return {k: _val(x) for k, x in asdict(v).items()}
    if isinstance(v, tuple):
        return [_val(x) for x in v]
    if isinstance(v, list):
        return [_val(x) for x in v]
    if isinstance(v, Mapping):
        return {str(k): _val(x) for k, x in v.items()}
    return v

def canonicalize_twitter_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    if not re.match(r"^[a-z]+://", raw, re.I):
        raw = "https://" + raw
    p = urlsplit(raw)
    host = p.netloc.lower().removeprefix("www.")
    path = re.sub(r"/+", "/", p.path or "/").rstrip("/") or "/"
    return f"https://{host}{path}"

def extract_twitter_source_id(canonical_url: str) -> str:
    p = urlsplit(canonical_url)
    return (p.netloc + p.path).strip("/")

def classify_twitter_route(url: str, capture_goal: str = "") -> str:
    canonical = canonicalize_twitter_url(url)
    path = urlsplit(canonical).path.strip("/").lower()
    goal = (capture_goal or "").lower()
    if "/status/" in path:
        return "single_status_media"
    if path.startswith("i/lists/") or "/lists/" in path:
        return "list_timeline_workaround"
    if path.startswith("i/bookmarks") or goal == "bookmarks":
        return "bookmarks_browser_export"
    if path.endswith("/likes") or goal == "likes":
        return "likes_browser_export"
    if path.startswith("i/article") or goal == "article":
        return "article_export_render"
    if path.endswith("/media") or goal == "user_media":
        return "user_media_timeline_strict_limited"
    if path and "/" not in path:
        return "user_timeline_strict_limited"
    if goal == "search" or path.startswith("search"):
        return "search_timeline"
    return "unknown_twitter_x_route"

def _a(order: int, component: str, action: str, reason: str = "") -> TwitterRouteAction:
    return TwitterRouteAction(order, component, action, reason)

def build_twitter_route_strategy(source_url: str, *, capture_goal: str = "", output_dir: str | Path = "", allow_untested_jdownloader: bool = True, capability_manifest_path: str | Path = "jd_capabilities_manifest.json") -> TwitterRouteStrategy:
    canonical = canonicalize_twitter_url(source_url)
    source_id = extract_twitter_source_id(canonical)
    kind = classify_twitter_route(canonical, capture_goal)
    common = (
        "Reimplement behaviour/algorithms in YTCE-owned modules; do not bulk-paste external source files unless deliberately vendored.",
        "Use a separate isolated test account/browser profile for X/Twitter browser/API-like capture.",
    )
    if kind == "single_status_media":
        plan = build_twitter_media_backend_plan(source_url=canonical, output_dir=output_dir or "twitter_media_downloads", allow_untested_jdownloader=allow_untested_jdownloader, capability_manifest_path=capability_manifest_path)
        return TwitterRouteStrategy(SCHEMA_VERSION, kind, source_url, canonical, source_id, capture_goal or "media", TWITTER_MEDIA_BACKEND_PROFILE_ID, ("browser_network_media_capture","manual_export_import"), (
            _a(1,"source_adapter","normalise public X/Twitter status URL"),
            _a(2,"shared_media_backend","try JDownloader API3128 public media route"),
            _a(3,"browser_capture","fallback to browser/network media capture if JD finds no media"),
            _a(4,"evidence","claim completed only when files or explicit no-media boundary are recorded"),
        ), (ISOLATE_TEST_ACCOUNT, RECORD_CURSOR_BOUNDARY), "complete_when_shared_backend_files_or_browser_media_inventory_is_recorded", "completed only when backend/browser capture produces files or explicit reviewed no-media state", common + (f"JD execution_allowed={plan.execution_allowed}; capability_found={plan.jdownloader_capability.capability_found}.",))
    if kind in {"user_timeline_strict_limited","user_media_timeline_strict_limited"}:
        return TwitterRouteStrategy(SCHEMA_VERSION, kind, source_url, canonical, source_id, capture_goal or "user_timeline", "browser_or_exporter_timeline_capture", ("list_timeline_workaround","manual_export_import","archive_snapshot"), (
            _a(1,"browser_or_exporter","capture timeline pages using logged-in isolated test profile"),
            _a(2,"twitter_api_boundary","record every returned cursor/page and stop reason"),
            _a(3,"list_workaround","optionally route target account through a private/list timeline"),
            _a(4,"media_backend","send discovered public media URLs to shared media backend"),
        ), (STRICT_USER_TWEETS_RATE_LIMIT, LIST_WORKAROUND_NOT_GUARANTEED, STOP_WHEN_NO_NEXT_PAGE, ISOLATE_TEST_ACCOUNT, RECORD_CURSOR_BOUNDARY, NO_FULL_CLAIM_WITHOUT_BOUNDARY), "partial_until_known_total_or_explicit_no_next_page_boundary", "do not claim full user export merely because one route stopped; record boundary and completeness state", common + ("rxliuli: user tweet export is strict/rate-limited.", "rxliuli: lists may work around it, but full export is not guaranteed.",))
    if kind == "list_timeline_workaround":
        return TwitterRouteStrategy(SCHEMA_VERSION, kind, source_url, canonical, source_id, capture_goal or "list_timeline", "list_timeline_workaround", ("manual_export_import","archive_snapshot"), (
            _a(1,"browser_or_exporter","capture list timeline with isolated profile"),
            _a(2,"twitter_api_boundary","record cursor/page boundary and no-next-page state"),
            _a(3,"media_backend","send discovered public media URLs to shared media backend"),
        ), (LIST_WORKAROUND_NOT_GUARANTEED, STOP_WHEN_NO_NEXT_PAGE, ISOLATE_TEST_ACCOUNT, RECORD_CURSOR_BOUNDARY, NO_FULL_CLAIM_WITHOUT_BOUNDARY), "complete_or_partial_based_on_recorded_cursor_boundary", "completion is tied to captured pages plus explicit cursor/no-next-page boundary", common)
    if kind in {"bookmarks_browser_export","likes_browser_export"}:
        return TwitterRouteStrategy(SCHEMA_VERSION, kind, source_url, canonical, source_id, capture_goal or kind, "browser_exporter_authenticated_capture", ("manual_export_import",), (
            _a(1,"browser_or_exporter","capture authenticated private timeline with isolated profile"),
            _a(2,"twitter_api_boundary","record cursor/rate-limit boundary"),
            _a(3,"local_export_import","preserve user-supplied exporter output and hashes"),
        ), (STRICT_USER_TWEETS_RATE_LIMIT, STOP_WHEN_NO_NEXT_PAGE, ISOLATE_TEST_ACCOUNT, RECORD_CURSOR_BOUNDARY, NO_FULL_CLAIM_WITHOUT_BOUNDARY), "complete_or_partial_based_on_recorded_cursor_boundary", "authenticated collection can claim completion only against the recorded account/session boundary", common)
    if kind == "article_export_render":
        return TwitterRouteStrategy(SCHEMA_VERSION, kind, source_url, canonical, source_id, capture_goal or "article", "x_article_exporter_style_pipeline", ("rendered_browser_capture","manual_pdf_import"), (
            _a(1,"article_extractor","extract X article content and metadata"),
            _a(2,"render_capture","render HTML/PDF/screenshot artifacts"),
            _a(3,"evidence","record source URL, rendered output, and extraction status"),
        ), (ISOLATE_TEST_ACCOUNT, RECORD_CURSOR_BOUNDARY), "complete_when_article_text_and_rendered_artifact_are_recorded", "completed when extracted text plus rendered artifact are produced", common)
    return TwitterRouteStrategy(SCHEMA_VERSION, kind, source_url, canonical, source_id, capture_goal or "unknown", "operator_review_required", (), (_a(1,"route_classifier","record unsupported or unknown X/Twitter route"),), (ISOLATE_TEST_ACCOUNT,), "not_started_until_route_selected", "no completion claim for unknown route", common)

def record_twitter_pagination_boundary(*, route_kind: str, source_url: str, page_number: int, returned_items_count: int, next_cursor: str = "", api_returned_next_page_data: bool = False, rate_limited: bool = False) -> TwitterPaginationBoundary:
    if rate_limited:
        reason, state = "rate_limited", "partial_rate_limited"
    elif next_cursor and api_returned_next_page_data:
        reason, state = "next_cursor_available", "in_progress"
    elif next_cursor and not api_returned_next_page_data:
        reason, state = "next_cursor_present_but_no_next_page_data_returned", "partial_api_boundary"
    else:
        reason, state = "no_next_cursor_or_no_next_page_data", "complete_if_known_total_else_partial_boundary"
    return TwitterPaginationBoundary(route_kind, source_url, int(page_number), int(returned_items_count), str(next_cursor or ""), bool(api_returned_next_page_data), bool(rate_limited), reason, state)

def write_twitter_route_strategy(path: str | Path, strategy: TwitterRouteStrategy) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(strategy.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return output
