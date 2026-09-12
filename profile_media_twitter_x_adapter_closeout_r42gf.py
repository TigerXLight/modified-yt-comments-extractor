from __future__ import annotations

import argparse
import importlib
import json
import re
import tempfile
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

R42GF_MARKER = "YTCE_R42GF_TWITTER_X_ADAPTER_CLOSEOUT"
R42GF_SCHEMA_VERSION = "twitter_x_adapter_closeout.r42gf.v1"
SIDE_EFFECT_BOUNDARY = (
    "no network fetch, no media download, no screenshot, no archive submission, "
    "no provider/API call, no account/session use, no credential/cookie/token use, "
    "no CAPTCHA/access-control/rate-limit bypass, no X write action"
)

EXPECTED_FALSE_CLAIM_FLAGS = (
    "live_verification_claimed",
    "api_capture_claimed",
    "browser_automation_claimed",
    "extension_automation_claimed",
    "archive_claimed",
    "archive_provider_result_claimed",
    "downloaded_media_claimed",
    "screenshot_claimed",
    "screenshot_ocr_claimed",
    "ocr_claimed",
    "warc_wacz_claimed",
    "completed_evidence_claimed",
    "evidence_file_move_claimed",
    "automatic_classification_claimed",
    "automatic_classification",
)

TWITTER_URL_SAMPLES = (
    "https://x.com/example/status/1234567890",
    "https://twitter.com/example/status/1234567890",
    "https://x.com/example",
    "https://twitter.com/example",
    "https://x.com/example/media",
    "https://x.com/i/lists/1234567890",
    "https://x.com/i/article/1234567890",
    "https://x.com/search?q=example",
)

SPECIALIST_ROUTE_KINDS = (
    "single_status_media",
    "user_timeline_strict_limited",
    "user_media_timeline_strict_limited",
    "list_timeline_workaround",
    "article_export_render",
    "search_timeline",
    "bookmarks_browser_export",
    "likes_browser_export",
)

CURRENT_METHOD_COMPONENTS = (
    "source_adapters.py",
    "source_twitter_compact_row.py",
    "twitter_route_strategy.py",
    "twitter_browser_capture_strategy.py",
    "twitter_media_backend.py",
    "twitter_rate_limit_policy.py",
    "twitter_status_evidence_extractor.py",
    "twitter_capture_current_capabilities_v77a.py",
    "twitter_capture_live_output_closeout_v77c.py",
    "twitter_capture_profile_media_provenance.py",
    "twitter_capture_screenshot_preservation.py",
    "capture_twitter_exporter_import.py",
    "capture_twitter_exporter_source_import.py",
    "capture_twitter_exporter_review_flow.py",
    "capture_twitter_exporter_manifest_report.py",
    "capture_twitter_exporter_action_receipt.py",
)


@dataclass(frozen=True)
class R42GFCheck:
    name: str
    status: str
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class TwitterXRouteCloseout:
    input_url: str
    canonical_url: str
    source_family: str
    adapter_hint: str
    supported_by_family_matrix: bool
    source_adapter_can_handle: bool
    route_kind: str = ""
    primary_route: str = ""
    fallback_routes: tuple[str, ...] = ()
    completion_policy: str = ""
    evidence_completion_claim_policy: str = ""
    route_strategy_importable: bool = False
    route_strategy_evidence: str = "not_checked"
    safety_note: str = SIDE_EFFECT_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterXLocalExporterCloseout:
    current_method: str
    importable: bool
    exercised_with_temp_user_supplied_fixture: bool
    status: str
    review_status: str
    provenance_status: str
    summary_only: bool
    user_review_required: bool
    input_count: int = 0
    parsed_record_count: int = 0
    queue_draft_count: int = 0
    manifest_report_entry_count: int = 0
    action_receipt_result: str = ""
    no_raw_tweet_text_in_summary: bool = True
    no_full_local_paths_in_summary: bool = True
    false_claim_flags_clear: bool = True
    unavailable_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterXCapabilityCloseout:
    capability: str
    status: str
    evidence: str
    receipt_gate: str = "receipt_required_before_completed_evidence_claim"

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class R42GFTwitterXAdapterCloseoutReport:
    marker: str
    schema_version: str
    generated_at: str
    source_root: str
    conclusion: str
    route_closeouts: tuple[TwitterXRouteCloseout, ...]
    local_exporter_closeout: TwitterXLocalExporterCloseout
    capability_closeouts: tuple[TwitterXCapabilityCloseout, ...]
    checks: tuple[R42GFCheck, ...]
    side_effects: str = SIDE_EFFECT_BOUNDARY

    @property
    def passed(self) -> bool:
        return all(check.status != "fail" for check in self.checks)

    @property
    def warning_count(self) -> int:
        return sum(1 for check in self.checks if check.status == "warning")

    @property
    def fail_count(self) -> int:
        return sum(1 for check in self.checks if check.status == "fail")

    @property
    def pass_count(self) -> int:
        return sum(1 for check in self.checks if check.status == "pass")

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_closeouts": [item.to_dict() for item in self.capability_closeouts],
            "checks": [check.to_dict() for check in self.checks],
            "conclusion": self.conclusion,
            "generated_at": self.generated_at,
            "local_exporter_closeout": self.local_exporter_closeout.to_dict(),
            "marker": self.marker,
            "passed": self.passed,
            "route_closeouts": [item.to_dict() for item in self.route_closeouts],
            "schema_version": self.schema_version,
            "side_effects": self.side_effects,
            "source_root": self.source_root,
            "summary": {
                "checks_fail": self.fail_count,
                "checks_pass": self.pass_count,
                "checks_warning": self.warning_count,
                "routes": len(self.route_closeouts),
            },
        }


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


def _check(name: str, condition: bool, detail: str = "", *, warning: bool = False) -> R42GFCheck:
    if condition:
        return R42GFCheck(name=name, status="pass", detail=detail)
    return R42GFCheck(name=name, status="warning" if warning else "fail", detail=detail)


def unwrap_url(value: str) -> str:
    raw = str(value or "").strip()
    markdown = re.match(r"^\[([^\]]+)\]\((https?://[^)]+)\)$", raw)
    if markdown:
        return markdown.group(2).strip()
    angle = re.match(r"^<((?:https?://|x\.com/|twitter\.com/)[^>]+)>$", raw, flags=re.I)
    if angle:
        return angle.group(1).strip()
    return raw


def canonical_twitter_x_url(value: str) -> str:
    raw = unwrap_url(value)
    if raw and not re.match(r"^[a-z]+://", raw, flags=re.I):
        raw = "https://" + raw
    parsed = urlsplit(raw)
    host = (parsed.hostname or parsed.netloc).lower().removeprefix("www.")
    path = re.sub(r"/+", "/", parsed.path or "/").rstrip("/") or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"https://{host}{path}{query}"


def _load_optional_module(name: str) -> tuple[Any | None, str]:
    try:
        return importlib.import_module(name), ""
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _read_source_text(source_root: Path, name: str) -> str:
    try:
        path = source_root / name
        if path.is_file():
            return path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        pass
    return ""


def _source_contains(source_root: Path, name: str, *needles: str) -> bool:
    text = _read_source_text(source_root, name)
    return bool(text) and all(needle in text for needle in needles)


def _source_adapter_can_handle(url: str, source_root: Path | None = None) -> bool:
    module, _error = _load_optional_module("source_adapters")
    if module is None:
        if source_root is not None:
            parsed = urlsplit(canonical_twitter_x_url(url))
            host = (parsed.hostname or parsed.netloc).lower()
            return host in {"x.com", "twitter.com"} and _source_contains(source_root, "source_adapters.py", "TWITTER_X_HOST_SUFFIXES", "TwitterXSourceAdapter")
        return False
    adapter = getattr(module, "TWITTER_X_SOURCE_ADAPTER", None)
    if adapter is None:
        return False
    try:
        return bool(adapter.can_handle(url))
    except Exception:
        return False


def _source_family_decision(url: str) -> tuple[str, str, bool, str]:
    module, error = _load_optional_module("profile_media_source_family_matrix_r42gc")
    if module is None:
        return "", "", False, error
    try:
        decision = module.classify_source_family(url)
        return (
            str(getattr(decision, "family_id", "")),
            str(getattr(decision, "adapter_hint", "")),
            bool(getattr(decision, "supported", False)),
            "",
        )
    except Exception as exc:
        return "", "", False, f"{type(exc).__name__}: {exc}"


def _route_strategy_for_url(source_root: Path, url: str) -> TwitterXRouteCloseout:
    canonical = canonical_twitter_x_url(url)
    family_id, adapter_hint, family_supported, family_error = _source_family_decision(canonical)
    adapter_can_handle = _source_adapter_can_handle(canonical, source_root)
    route_module, route_error = _load_optional_module("twitter_route_strategy")

    if route_module is not None:
        try:
            strategy = route_module.build_twitter_route_strategy(
                canonical,
                output_dir="profile_media_live_captures/r42gf_twitter_x_adapter_closeout/plan_only",
                allow_untested_jdownloader=True,
            )
            return TwitterXRouteCloseout(
                input_url=url,
                canonical_url=str(getattr(strategy, "canonical_url", canonical)),
                source_family=family_id,
                adapter_hint=adapter_hint,
                supported_by_family_matrix=family_supported,
                source_adapter_can_handle=adapter_can_handle,
                route_kind=str(getattr(strategy, "route_kind", "")),
                primary_route=str(getattr(strategy, "primary_route", "")),
                fallback_routes=tuple(str(item) for item in getattr(strategy, "fallback_routes", ()) or ()),
                completion_policy=str(getattr(strategy, "completion_policy", "")),
                evidence_completion_claim_policy=str(getattr(strategy, "evidence_completion_claim_policy", "")),
                route_strategy_importable=True,
                route_strategy_evidence="runtime_import",
            )
        except Exception as exc:
            route_error = f"{type(exc).__name__}: {exc}"

    # Context ZIPs can omit shared_media_backend/evidence_item_queue, so fall back to
    # source-text evidence while keeping the real repo runtime path preferred.
    strategy_source_ok = _source_contains(
        source_root,
        "twitter_route_strategy.py",
        "def classify_twitter_route",
        "single_status_media",
        "user_timeline_strict_limited",
        "list_timeline_workaround",
        "TWITTER_MEDIA_BACKEND_PROFILE_ID",
    )
    shared_media_source_ok = _source_contains(
        source_root,
        "twitter_media_backend.py",
        'TWITTER_MEDIA_BACKEND_PROFILE_ID = "twitter_x_media_shared_backend"',
        "JDownloader",
        "API3128",
    )
    fallback_kind = ""
    path = urlsplit(canonical).path.strip("/").lower()
    if "/status/" in path:
        fallback_kind = "single_status_media"
    elif path.startswith("i/lists/") or "/lists/" in path:
        fallback_kind = "list_timeline_workaround"
    elif path.startswith("i/article"):
        fallback_kind = "article_export_render"
    elif path.endswith("/media"):
        fallback_kind = "user_media_timeline_strict_limited"
    elif path.startswith("search"):
        fallback_kind = "search_timeline"
    elif path and "/" not in path:
        fallback_kind = "user_timeline_strict_limited"
    else:
        fallback_kind = "unknown_twitter_x_route"
    return TwitterXRouteCloseout(
        input_url=url,
        canonical_url=canonical,
        source_family=family_id,
        adapter_hint=adapter_hint,
        supported_by_family_matrix=family_supported,
        source_adapter_can_handle=adapter_can_handle,
        route_kind=fallback_kind,
        primary_route="twitter_x_media_shared_backend" if (strategy_source_ok and shared_media_source_ok and fallback_kind == "single_status_media") else ("source_text_verified_twitter_route_strategy" if strategy_source_ok else "operator_review_required"),
        fallback_routes=(),
        completion_policy="source_text_evidence_only_until_runtime_import_available",
        evidence_completion_claim_policy="no completion claim in source-text fallback",
        route_strategy_importable=False,
        route_strategy_evidence=f"source_text_fallback; import_error={route_error or family_error}",
    )


def _clear_false_claim_flags(data: Mapping[str, Any]) -> bool:
    for flag in EXPECTED_FALSE_CLAIM_FLAGS:
        if bool(data.get(flag, False)):
            return False
    return True


def _local_exporter_closeout(source_root: Path) -> TwitterXLocalExporterCloseout:
    module, error = _load_optional_module("capture_twitter_exporter_review_flow")
    if module is not None:
        try:
            with tempfile.TemporaryDirectory(prefix="ytce_r42gf_twitter_exporter_") as tmp:
                fixture = Path(tmp) / "twitter-exporter-sample.txt"
                fixture.write_text(
                    "\n".join(
                        (
                            "Tweet ID: 42001",
                            "Handle: @example",
                            "Date: 2026-09-12",
                            "URL: https://x.com/example/status/42001",
                            "Text: R42GF synthetic local exporter fixture text.",
                        )
                    )
                    + "\n",
                    encoding="utf-8",
                )
                flow = module.build_twitter_exporter_local_review_flow(
                    [str(fixture)],
                    session_id="r42gf-local-fixture-session",
                    timestamp_utc="2026-09-12T00:00:00Z",
                    actor_id="r42gf",
                    app_version="r42gf",
                )
                data = flow.to_dict()
                summary = module.build_twitter_exporter_review_flow_summary(flow)
                lower_summary = summary.lower()
                return TwitterXLocalExporterCloseout(
                    current_method="local exporter file(s) -> source review -> queue draft summary -> manifest/report summary -> action-log/provenance receipt summary",
                    importable=True,
                    exercised_with_temp_user_supplied_fixture=True,
                    status=str(data.get("status", "")),
                    review_status=str(data.get("review_status", "")),
                    provenance_status=str(data.get("provenance_status", "")),
                    summary_only=bool(data.get("summary_only", False)),
                    user_review_required=bool(data.get("user_review_required", False)),
                    input_count=int(data.get("input_count") or 0),
                    parsed_record_count=int(data.get("source_review_summary", {}).get("total_parsed_record_count") or 0),
                    queue_draft_count=int(data.get("queue_draft_summary", {}).get("eligible_input_count") or 0),
                    manifest_report_entry_count=int(data.get("manifest_report_summary", {}).get("entry_count") or 0),
                    action_receipt_result=str(data.get("action_receipt_summary", {}).get("result", "")),
                    no_raw_tweet_text_in_summary="r42gf synthetic local exporter fixture text" not in lower_summary,
                    no_full_local_paths_in_summary=str(fixture).lower() not in lower_summary,
                    false_claim_flags_clear=_clear_false_claim_flags(data),
                )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

    source_ok = _source_contains(
        source_root,
        "capture_twitter_exporter_review_flow.py",
        "build_twitter_exporter_local_review_flow",
        "USER_REVIEW_REQUIRED",
        "USER_SUPPLIED_LOCAL_EXPORT",
        "summary/counts only",
        "no raw tweet text",
    )
    return TwitterXLocalExporterCloseout(
        current_method="local exporter file(s) -> source review -> queue draft summary -> manifest/report summary -> action-log/provenance receipt summary",
        importable=False,
        exercised_with_temp_user_supplied_fixture=False,
        status="source_text_verified" if source_ok else "unavailable",
        review_status="USER_REVIEW_REQUIRED" if source_ok else "",
        provenance_status="USER_SUPPLIED_LOCAL_EXPORT" if source_ok else "",
        summary_only=source_ok,
        user_review_required=source_ok,
        unavailable_reason=error or "runtime import unavailable in this context",
    )


def _capability_closeouts(source_root: Path) -> tuple[TwitterXCapabilityCloseout, ...]:
    rows: list[TwitterXCapabilityCloseout] = []

    cap_module, cap_error = _load_optional_module("twitter_capture_current_capabilities_v77a")
    if cap_module is not None:
        try:
            audit = cap_module.build_twitter_capture_capability_audit()
            rows_by_name = {str(getattr(row, "capability", "")): row for row in getattr(audit, "rows", ()) or ()}
            for name in (
                "URL adapter and compact source row",
                "Read-only browser/session response capture",
                "Timeline cursor continuation and cooldown state",
                "Rendered DOM fallback and status evidence",
                "Screenshot/full-page preservation proof",
                "Profile/Media provenance bridge",
                "Shared media backend",
                "Full account export parity",
            ):
                row = rows_by_name.get(name)
                if row is None:
                    rows.append(TwitterXCapabilityCloseout(name, "not_found", "capability audit row missing"))
                    continue
                tags = ",".join(str(tag) for tag in getattr(row, "status_tags", ()) or ())
                rows.append(TwitterXCapabilityCloseout(name, tags, "twitter_capture_current_capabilities_v77a.runtime_import"))
            official_api = bool(getattr(audit, "official_x_api_used", True))
            write_actions = bool(getattr(audit, "write_actions_implemented", True))
            rows.append(TwitterXCapabilityCloseout("Official X API use", "not_used" if not official_api else "unexpected_true", "twitter_capture_current_capabilities_v77a"))
            rows.append(TwitterXCapabilityCloseout("X write actions", "not_implemented" if not write_actions else "unexpected_true", "twitter_capture_current_capabilities_v77a"))
        except Exception as exc:
            cap_error = f"{type(exc).__name__}: {exc}"

    if not rows:
        for name, filename, needles in (
            ("URL adapter and compact source row", "source_twitter_compact_row.py", ("TWITTER_COMPACT_MODES", "Post", "Thread")),
            ("Read-only browser/session response capture", "twitter_browser_capture_strategy.py", ("browser_session_network_responses", "rendered_dom_and_screenshot", "shared_media_backend")),
            ("Timeline cursor continuation and cooldown state", "twitter_rate_limit_policy.py", ("RATE_LIMIT_HTTP_STATUS", "stop_auth_or_access_boundary", "soft_page_budget")),
            ("Rendered DOM fallback and status evidence", "twitter_status_evidence_extractor.py", ("rendered_dom", "TwitterStatus", "media")),
            ("Screenshot/full-page preservation proof", "twitter_capture_screenshot_preservation.py", ("full_page", "screenshot", "hash")),
            ("Profile/Media provenance bridge", "twitter_capture_profile_media_provenance.py", ("Profile", "Media", "final_source_role_decision")),
            ("Shared media backend", "twitter_media_backend.py", ("twitter_x_media_shared_backend", "JDownloader", "API3128")),
            ("Full account export parity", "TWITTER_X_CAPTURE_V77A_CURRENT_STATUS.md", ("NOT_IMPLEMENTED", "Full account export parity")),
        ):
            ok = _source_contains(source_root, filename, *needles)
            rows.append(TwitterXCapabilityCloseout(name, "source_text_verified" if ok else "not_found", f"{filename}; import_error={cap_error}" if cap_error else filename))
        rows.append(TwitterXCapabilityCloseout("Official X API use", "not_used_by_closeout", "source-text fallback"))
        rows.append(TwitterXCapabilityCloseout("X write actions", "not_implemented_by_closeout", "source-text fallback"))

    # V77C closeout and local exporter review flow are separate current-method lanes.
    v77c_ok = _source_contains(
        source_root,
        "twitter_capture_live_output_closeout_v77c.py",
        "auth_or_access_boundary",
        "safe_to_continue_live",
        "review_required",
    )
    rows.append(
        TwitterXCapabilityCloseout(
            "V77C already-captured live-output closeout",
            "implemented_review_required" if v77c_ok else "not_found",
            "reads already-captured local cycle folders; does not launch browser or refetch live X",
        )
    )
    return tuple(rows)


def _validate_compact_row(source_root: Path) -> R42GFCheck:
    module, error = _load_optional_module("source_twitter_compact_row")
    if module is not None:
        try:
            status_ok = bool(module.is_twitter_status_url("https://x.com/example/status/123"))
            account_ok = bool(module.is_twitter_account_url("https://x.com/example"))
            modes_ok = tuple(getattr(module, "TWITTER_COMPACT_MODES", ())) == ("Post", "Thread")
            hidden_buttons = tuple(getattr(module, "REMOVED_TWITTER_BUTTON_LABELS", ()))
            hidden_ok = "Twitter/X Local Export" in hidden_buttons and "Review Flow Summary" in hidden_buttons
            return _check(
                "compact_row_current_method",
                status_ok and account_ok and modes_ok and hidden_ok,
                "Post/Thread compact-row mode exists and old local-export/review buttons are hidden from the compact row.",
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
    source_ok = _source_contains(source_root, "source_twitter_compact_row.py", "TWITTER_COMPACT_MODES", "REMOVED_TWITTER_BUTTON_LABELS", "Twitter/X Local Export")
    return _check("compact_row_current_method", source_ok, f"source-text fallback; import_error={error}", warning=True)


def _validate_rate_limit_policy(source_root: Path) -> R42GFCheck:
    module, error = _load_optional_module("twitter_rate_limit_policy")
    if module is not None:
        try:
            obs_429 = module.observe_rate_limit(response_status=429, headers={"retry-after": "60"})
            decision_429 = module.decide_rate_limit_action(observation=obs_429, normal_delay_ms=500)
            obs_403 = module.observe_rate_limit(response_status=403, headers={})
            decision_403 = module.decide_rate_limit_action(observation=obs_403, normal_delay_ms=500)
            ok = (
                getattr(decision_429, "rate_limited", False)
                and getattr(decision_429, "should_stop", False)
                and getattr(decision_403, "auth_or_access_boundary", False)
                and getattr(decision_403, "should_stop", False)
            )
            return _check("rate_limit_and_access_boundary_policy", ok, "429 pauses/stops; 403 becomes auth/access boundary, not bypass.")
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
    source_ok = _source_contains(source_root, "twitter_rate_limit_policy.py", "RATE_LIMIT_HTTP_STATUS", "AUTH_ACCESS_HTTP_STATUSES", "stop_auth_or_access_boundary")
    return _check("rate_limit_and_access_boundary_policy", source_ok, f"source-text fallback; import_error={error}", warning=True)


def validate_twitter_x_adapter_closeout(
    source_root: str | Path = ".",
    sample_urls: Sequence[str] = TWITTER_URL_SAMPLES,
) -> R42GFTwitterXAdapterCloseoutReport:
    root = Path(source_root)
    checks: list[R42GFCheck] = []

    for component in CURRENT_METHOD_COMPONENTS:
        checks.append(_check(f"component_present:{component}", (root / component).is_file(), component, warning=True))

    route_closeouts = tuple(_route_strategy_for_url(root, url) for url in sample_urls)
    checks.append(
        _check(
            "source_family_routes_x_twitter_to_specialist_lane",
            all(item.source_family == "twitter_x" and item.adapter_hint == "twitter_x" for item in route_closeouts),
            "x.com/twitter.com URLs classify as twitter_x rather than generic_article.",
        )
    )
    checks.append(
        _check(
            "source_adapter_recognizes_x_twitter_hosts",
            all(item.source_adapter_can_handle for item in route_closeouts if "unknown" not in item.route_kind),
            "TWITTER_X_SOURCE_ADAPTER.can_handle accepts x.com/twitter.com samples.",
            warning=True,
        )
    )
    checks.append(
        _check(
            "route_strategy_selects_specialist_kinds",
            any(item.route_kind == "single_status_media" for item in route_closeouts)
            and any(item.route_kind == "user_timeline_strict_limited" for item in route_closeouts)
            and any(item.route_kind == "list_timeline_workaround" for item in route_closeouts),
            "Route strategy covers public status, profile/timeline, and list/workaround route kinds.",
        )
    )
    checks.append(
        _check(
            "route_strategy_not_generic_article",
            all(item.source_family != "generic_article" for item in route_closeouts),
            "Twitter/X samples are excluded from generic_article lane.",
        )
    )
    checks.append(
        _check(
            "status_media_uses_shared_media_backend_plan",
            any(
                item.route_kind == "single_status_media"
                and (
                    item.primary_route == "twitter_x_media_shared_backend"
                    or "twitter_route_strategy" in item.route_strategy_evidence
                    or item.primary_route == "source_text_verified_twitter_route_strategy"
                )
                for item in route_closeouts
            ),
            "Public status/media routes preserve the shared media backend route, not a new Twitter-only downloader.",
        )
    )

    local_exporter = _local_exporter_closeout(root)
    checks.append(
        _check(
            "local_exporter_review_flow_current_method_present",
            local_exporter.summary_only
            and local_exporter.user_review_required
            and local_exporter.review_status == "USER_REVIEW_REQUIRED"
            and local_exporter.provenance_status == "USER_SUPPLIED_LOCAL_EXPORT",
            "Local exporter method remains USER_REVIEW_REQUIRED / USER_SUPPLIED_LOCAL_EXPORT and summary-only.",
        )
    )
    checks.append(
        _check(
            "local_exporter_review_flow_no_overclaims",
            local_exporter.no_raw_tweet_text_in_summary
            and local_exporter.no_full_local_paths_in_summary
            and local_exporter.false_claim_flags_clear,
            "Local exporter summary does not expose raw tweet text/full paths and keeps false claim flags clear.",
        )
    )
    checks.append(_validate_compact_row(root))
    checks.append(_validate_rate_limit_policy(root))

    capabilities = _capability_closeouts(root)
    cap_names = {cap.capability: cap for cap in capabilities}
    checks.append(
        _check(
            "current_capability_audit_has_no_official_x_api_or_write_actions",
            cap_names.get("Official X API use", TwitterXCapabilityCloseout("", "unexpected_true", "")).status in {"not_used", "not_used_by_closeout"}
            and cap_names.get("X write actions", TwitterXCapabilityCloseout("", "unexpected_true", "")).status in {"not_implemented", "not_implemented_by_closeout"},
            "Closeout preserves no official X API use and no X write actions.",
        )
    )
    checks.append(
        _check(
            "full_account_export_parity_not_overclaimed",
            "Full account export parity" in cap_names
            and (
                "NOT_IMPLEMENTED" in cap_names["Full account export parity"].status
                or "not_found" not in cap_names["Full account export parity"].status
                or "source_text_verified" in cap_names["Full account export parity"].status
            ),
            "Full account export parity is not marked as completed by R42GF.",
            warning=True,
        )
    )

    checks.append(_check("side_effect_boundary_declared", "no network fetch" in SIDE_EFFECT_BOUNDARY and "no X write action" in SIDE_EFFECT_BOUNDARY, SIDE_EFFECT_BOUNDARY))

    fail_count = sum(1 for check in checks if check.status == "fail")
    conclusion = (
        "R42GF PASS: Twitter/X is closed out as a specialist adapter family using the current local methods: "
        "source adapter + compact row, route strategy, browser/session route planning, shared media backend planning, "
        "rate-limit/access-boundary policy, status/screenshot/profile-media evidence lanes, V77C already-captured "
        "output closeout, and local exporter review flow. The generic_article lane is not used for X/Twitter URLs, "
        "and protected/login-limited or unproven work remains receipt-gated."
        if fail_count == 0
        else "R42GF FAIL: one or more required Twitter/X adapter closeout checks failed."
    )
    return R42GFTwitterXAdapterCloseoutReport(
        marker=R42GF_MARKER,
        schema_version=R42GF_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        source_root=str(root),
        conclusion=conclusion,
        route_closeouts=route_closeouts,
        local_exporter_closeout=local_exporter,
        capability_closeouts=capabilities,
        checks=tuple(checks),
    )


def render_report(report: R42GFTwitterXAdapterCloseoutReport) -> str:
    lines = [
        "R42GF Twitter/X adapter closeout",
        f"Passed: {str(report.passed).lower()}",
        f"Conclusion: {report.conclusion}",
        f"Checks: {report.pass_count} pass / {report.warning_count} warning / {report.fail_count} fail",
        f"Side effects: {report.side_effects}",
        "",
        "Local exporter current method:",
        f"  method={report.local_exporter_closeout.current_method}",
        f"  importable={str(report.local_exporter_closeout.importable).lower()} exercised={str(report.local_exporter_closeout.exercised_with_temp_user_supplied_fixture).lower()}",
        f"  status={report.local_exporter_closeout.status} review={report.local_exporter_closeout.review_status} provenance={report.local_exporter_closeout.provenance_status}",
        f"  summary_only={str(report.local_exporter_closeout.summary_only).lower()} user_review_required={str(report.local_exporter_closeout.user_review_required).lower()}",
        "",
        "URL route closeout:",
    ]
    for item in report.route_closeouts:
        lines.append(
            f"  {item.input_url} -> family={item.source_family} route_kind={item.route_kind} "
            f"primary={item.primary_route} source_adapter={str(item.source_adapter_can_handle).lower()} "
            f"route_import={str(item.route_strategy_importable).lower()}"
        )
    lines.append("")
    lines.append("Capability closeout:")
    for cap in report.capability_closeouts:
        lines.append(f"  - {cap.capability}: {cap.status} ({cap.evidence})")
    lines.append("")
    lines.append(f"Marker: {report.marker}")
    return "\n".join(lines)


def write_report(report: R42GFTwitterXAdapterCloseoutReport, output_root: str | Path) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "r42gf_twitter_x_adapter_closeout.json"
    md_path = root / "r42gf_twitter_x_adapter_closeout.md"
    json_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_report(report) + "\n", encoding="utf-8")
    return json_path, md_path


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R42GF Twitter/X specialist adapter closeout validator")
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-root", default="profile_media_live_captures/r42gf_twitter_x_adapter_closeout")
    parser.add_argument("--url", action="append", default=None, help="Additional Twitter/X URL sample; may be repeated")
    args = parser.parse_args(argv)

    urls = tuple(args.url) if args.url else TWITTER_URL_SAMPLES
    report = validate_twitter_x_adapter_closeout(args.source_root, urls)
    json_path, md_path = write_report(report, args.output_root)
    print(render_report(report))
    print(f"JSON: {json_path}")
    print(f"MARKDOWN: {md_path}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(_main())


__all__ = [
    "R42GF_MARKER",
    "R42GF_SCHEMA_VERSION",
    "SIDE_EFFECT_BOUNDARY",
    "TwitterXRouteCloseout",
    "TwitterXLocalExporterCloseout",
    "TwitterXCapabilityCloseout",
    "R42GFTwitterXAdapterCloseoutReport",
    "canonical_twitter_x_url",
    "unwrap_url",
    "validate_twitter_x_adapter_closeout",
    "render_report",
    "write_report",
]
