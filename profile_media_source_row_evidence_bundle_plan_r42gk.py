from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from profile_media_source_map_raw_url_audio_catchup_r42gh import GLOBAL_PLAYER_METHOD_METADATA, R42GH_PASS_STATUS, validate_source_map_raw_url_audio_catchup
from profile_media_universal_evidence_bundle_index_r42gj import (
    PROMOTION_NONE,
    R42GJ_PASS_STATUS,
    ROLE_STATUS_COMPAT,
    build_report as build_r42gj_report,
    build_global_player_audio_record,
    build_news_article_record,
    build_twitter_single_post_record,
    build_twitter_timeline_record,
)
from profile_media_universal_media_method_matrix_r42gi import (
    R42GI_PASS_STATUS,
    build_generic_article_sample_media_candidate,
    build_global_player_media_candidate,
    build_twitter_sample_media_candidate,
    validate_universal_media_method_matrix,
)
from profile_media_universal_source_map_r42gg import (
    R42GG_PASS_STATUS,
    SIDE_EFFECT_BOUNDARY,
    STATUS_METADATA_ONLY_UNTIL_CAPTURED,
    STATUS_PROHIBITED_NO_BYPASS,
    STATUS_REVIEW_REQUIRED,
    detect_source_family,
    sanitize_source_url,
    validate_universal_source_map,
)

R42GK_MARKER = "YTCE_R42GK_SOURCE_ROW_EVIDENCE_BUNDLE_PLAN_BRIDGE"
R42GK_PASS_STATUS = "PASS_R42GK_SOURCE_ROW_EVIDENCE_BUNDLE_PLAN_BRIDGE"
R42GK_BLOCKED_STATUS = "BLOCKED_R42GK_WITH_EXACT_BLOCKER"
R42GK_SCHEMA_VERSION = "source_row_evidence_bundle_plan_bridge.r42gk.v1"
DEFAULT_CAPTURE_TIMESTAMP = "20260913T000000Z"

SOURCE_ROW_INPUT_SCHEMA_FIELDS: tuple[str, ...] = (
    "row_id",
    "raw_input",
    "source_url",
    "source_title",
    "source_label",
    "source_family_hint",
    "source_candidate_id",
    "capture_mode_hint",
    "capture_method_hint",
    "selected_for_capture",
    "requires_review",
    "created_at_text",
    "notes",
    "raw_row_payload",
)

EVIDENCE_BUNDLE_PLAN_SCHEMA_FIELDS: tuple[str, ...] = (
    "schema_version",
    "plan_id",
    "row_id",
    "source_candidate_id",
    "source_family",
    "record_type",
    "platform_or_provider",
    "source_url",
    "canonical_url",
    "raw_url",
    "bundle_id",
    "root_output_path",
    "manifest_path",
    "records_index_path",
    "review_strings_path",
    "media_index_path",
    "comments_index_path",
    "replies_index_path",
    "progress_events_path",
    "audit_log_path",
    "source_role_bridge_path",
    "expected_record_paths",
    "expected_child_paths",
    "expected_media_candidate_ids",
    "review_strings",
    "source_role_bridge_status",
    "promotion_status",
    "review_status",
    "access_status",
    "requires_human_chain",
    "requires_login",
    "requires_manual_receipt",
    "capture_method_id",
    "allowed_methods",
    "blocked_methods",
    "blocked_reason",
    "side_effect_boundary",
    "no_jump_counter_safe",
)

MACHINE_URL_FIELDS = {"source_url", "canonical_url", "raw_url", "canonical_media_url", "source_row_url"}


@dataclass(frozen=True)
class SourceRowInput:
    row_id: str
    raw_input: str
    source_url: str = ""
    source_title: str = ""
    source_label: str = ""
    source_family_hint: str = ""
    source_candidate_id: str = ""
    capture_mode_hint: str = ""
    capture_method_hint: str = ""
    selected_for_capture: bool = False
    requires_review: bool = True
    created_at_text: str = ""
    notes: str = ""
    raw_row_payload: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["raw_row_payload"] = dict(self.raw_row_payload or {})
        return data


@dataclass(frozen=True)
class PlannedChildPath:
    kind: str
    path: str
    description: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class PlannedReviewString:
    value: str
    kind: str
    source: str = "source_row_plan"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class PlannedSourceRoleBridge:
    bridge_id: str
    bundle_id: str
    evidence_id: str
    source_candidate_id: str
    source_family: str
    candidate_kind: str
    review_strings: tuple[str, ...]
    role_hint: str = "none"
    role_status: str = ROLE_STATUS_COMPAT
    promotion_status: str = PROMOTION_NONE
    blocked_reason: str = ""
    requires_review: bool = True
    source_role_compatible: bool = True
    no_jump_counter_safe: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["review_strings"] = list(self.review_strings)
        return data


@dataclass(frozen=True)
class EvidenceBundlePlan:
    plan_id: str
    row_id: str
    source_candidate_id: str
    source_family: str
    record_type: str
    platform_or_provider: str
    source_url: str
    canonical_url: str
    raw_url: str
    bundle_id: str
    root_output_path: str
    manifest_path: str
    records_index_path: str
    review_strings_path: str
    media_index_path: str
    comments_index_path: str
    replies_index_path: str
    progress_events_path: str
    audit_log_path: str
    source_role_bridge_path: str
    expected_record_paths: tuple[str, ...]
    expected_child_paths: tuple[PlannedChildPath, ...]
    expected_media_candidate_ids: tuple[str, ...]
    review_strings: tuple[PlannedReviewString, ...]
    source_role_bridge_status: str = ROLE_STATUS_COMPAT
    promotion_status: str = PROMOTION_NONE
    review_status: str = STATUS_REVIEW_REQUIRED
    access_status: str = STATUS_REVIEW_REQUIRED
    requires_human_chain: bool = False
    requires_login: bool = False
    requires_manual_receipt: bool = False
    capture_method_id: str = ""
    allowed_methods: tuple[str, ...] = ()
    blocked_methods: tuple[str, ...] = ()
    blocked_reason: str = ""
    side_effect_boundary: str = SIDE_EFFECT_BOUNDARY
    no_jump_counter_safe: bool = True
    schema_version: str = R42GK_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["expected_child_paths"] = [path.to_dict() for path in self.expected_child_paths]
        data["review_strings"] = [item.to_dict() for item in self.review_strings]
        data["expected_media_candidate_ids"] = list(self.expected_media_candidate_ids)
        data["expected_record_paths"] = list(self.expected_record_paths)
        data["allowed_methods"] = list(self.allowed_methods)
        data["blocked_methods"] = list(self.blocked_methods)
        return data


@dataclass(frozen=True)
class R42GKReport:
    marker: str
    schema_version: str
    generated_at: str
    source_root: str
    status: str
    source_row_input_schema: Mapping[str, Any]
    evidence_bundle_plan_schema: Mapping[str, Any]
    sample_plans: tuple[Mapping[str, Any], ...]
    sample_source_role_bridges: tuple[Mapping[str, Any], ...]
    sample_review_string_index_links: tuple[Mapping[str, Any], ...]
    checks: tuple[Mapping[str, str], ...]
    side_effect_boundary: str = SIDE_EFFECT_BOUNDARY

    @property
    def passed(self) -> bool:
        return self.status == R42GK_PASS_STATUS and all(check.get("status") != "fail" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [dict(check) for check in self.checks],
            "evidence_bundle_plan_schema": dict(self.evidence_bundle_plan_schema),
            "generated_at": self.generated_at,
            "marker": self.marker,
            "passed": self.passed,
            "sample_plans": [dict(plan) for plan in self.sample_plans],
            "sample_review_string_index_links": [dict(item) for item in self.sample_review_string_index_links],
            "sample_source_role_bridges": [dict(bridge) for bridge in self.sample_source_role_bridges],
            "schema_version": self.schema_version,
            "side_effect_boundary": self.side_effect_boundary,
            "source_root": self.source_root,
            "source_row_input_schema": dict(self.source_row_input_schema),
            "status": self.status,
        }


def _check(name: str, condition: bool, detail: str = "") -> Mapping[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _schema(fields: Sequence[str]) -> Mapping[str, Any]:
    return {"schema_version": R42GK_SCHEMA_VERSION, "fields": list(fields)}


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return tuple(output)


def _fingerprint(values: Sequence[str]) -> str:
    payload = "|".join(str(value or "") for value in values)
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()[:24]


def _safe_segment(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.@-]+", "_", str(value or "")).strip("_")
    return cleaned or fallback


def _source_url(row: SourceRowInput) -> str:
    return row.source_url or row.raw_input


def _x_parts(canonical_url: str) -> tuple[str, str]:
    parts = urlsplit(canonical_url)
    pieces = [piece for piece in parts.path.split("/") if piece]
    handle = pieces[0] if pieces else "account"
    post_id = ""
    if "status" in pieces:
        index = pieces.index("status")
        if index + 1 < len(pieces):
            post_id = pieces[index + 1]
    return handle, post_id


def _record_review_strings(plan: EvidenceBundlePlan) -> tuple[str, ...]:
    return _dedupe([item.value for item in plan.review_strings])


def _planned_strings(values: Sequence[str], kind: str = "review") -> tuple[PlannedReviewString, ...]:
    return tuple(PlannedReviewString(value=value, kind=kind) for value in _dedupe(values))


def _plan_id(row_id: str, canonical: str, record_type: str) -> str:
    return f"plan:{_safe_segment(row_id, 'row')}:{record_type}:{_fingerprint([canonical, record_type])}"


def _base_plan(
    *,
    row: SourceRowInput,
    canonical: str,
    source_family: str,
    record_type: str,
    platform_or_provider: str,
    bundle_id: str,
    root_output_path: str,
    expected_record_paths: Sequence[str],
    expected_child_paths: Sequence[PlannedChildPath],
    expected_media_candidate_ids: Sequence[str],
    review_strings: Sequence[str],
    capture_method_id: str,
    allowed_methods: Sequence[str],
    access_status: str = STATUS_REVIEW_REQUIRED,
    review_status: str = STATUS_REVIEW_REQUIRED,
    requires_human_chain: bool = False,
    requires_login: bool = False,
    requires_manual_receipt: bool = False,
    blocked_methods: Sequence[str] = (),
    blocked_reason: str = "",
) -> EvidenceBundlePlan:
    raw_url = _source_url(row)
    return EvidenceBundlePlan(
        plan_id=_plan_id(row.row_id, canonical, record_type),
        row_id=row.row_id,
        source_candidate_id=row.source_candidate_id or f"source_candidate:{_fingerprint([canonical, row.row_id])}",
        source_family=source_family,
        record_type=record_type,
        platform_or_provider=platform_or_provider,
        source_url=canonical,
        canonical_url=canonical,
        raw_url=sanitize_source_url(raw_url),
        bundle_id=bundle_id,
        root_output_path=root_output_path,
        manifest_path=f"{root_output_path}/manifest.json",
        records_index_path=f"{root_output_path}/records.ndjson",
        review_strings_path=f"{root_output_path}/review_strings.txt",
        media_index_path=f"{root_output_path}/media_index.json",
        comments_index_path=f"{root_output_path}/comments/",
        replies_index_path=f"{root_output_path}/replies/",
        progress_events_path=f"{root_output_path}/progress_events.ndjson",
        audit_log_path=f"{root_output_path}/audit_log.ndjson",
        source_role_bridge_path=f"{root_output_path}/source_role_bridge.json",
        expected_record_paths=tuple(expected_record_paths),
        expected_child_paths=tuple(expected_child_paths),
        expected_media_candidate_ids=tuple(expected_media_candidate_ids),
        review_strings=_planned_strings(review_strings),
        access_status=access_status,
        review_status=review_status,
        requires_human_chain=requires_human_chain,
        requires_login=requires_login,
        requires_manual_receipt=requires_manual_receipt,
        capture_method_id=capture_method_id,
        allowed_methods=tuple(allowed_methods),
        blocked_methods=tuple(blocked_methods),
        blocked_reason=blocked_reason,
    )


def build_evidence_bundle_plan_from_source_row(row: SourceRowInput, capture_timestamp: str = DEFAULT_CAPTURE_TIMESTAMP) -> EvidenceBundlePlan:
    canonical = sanitize_source_url(_source_url(row))
    family = row.source_family_hint or detect_source_family(canonical)
    lowered_hints = " ".join([row.source_family_hint, row.capture_mode_hint, row.capture_method_hint, row.notes]).lower()
    if any(token in lowered_hints for token in ("private", "login", "blocked", "prohibited")):
        return build_unknown_or_blocked_plan(row, canonical, family, capture_timestamp, blocked_reason="source_row_marked_private_login_blocked_or_prohibited")
    if family == "twitter_x":
        handle, post_id = _x_parts(canonical)
        if post_id:
            return build_twitter_post_plan(row, canonical, handle, post_id, capture_timestamp)
        return build_twitter_timeline_plan(row, canonical, handle, capture_timestamp)
    if family == "public_broadcast_catchup_audio" or "globalplayer.com" in canonical:
        return build_public_audio_plan(row, canonical, capture_timestamp)
    if family in {"news_websites", "generic_web_article_media"} or "metro.co.uk" in canonical:
        return build_news_article_plan(row, canonical, capture_timestamp)
    return build_unknown_or_blocked_plan(row, canonical, family, capture_timestamp, blocked_reason="unsupported_or_unknown_source_row_review_only")


def build_twitter_post_plan(row: SourceRowInput, canonical: str, handle: str, post_id: str, capture_timestamp: str) -> EvidenceBundlePlan:
    known = build_twitter_single_post_record() if canonical == "https://x.com/BBCr4today/status/2097217541416308845" else None
    root = f"source_exports/twitter_x/{_safe_segment(handle, 'account')}/capture_{capture_timestamp}/posts/{post_id}"
    media_id = f"media:twitter_x:{handle}:{post_id}:receipt_media"
    review_strings = [
        canonical,
        f"twitter_x:post:{post_id}",
        post_id,
        f"@{handle}",
        root,
        f"posts/{post_id}/media/",
        f"posts/{post_id}/comments/",
        f"posts/{post_id}/replies/",
    ]
    if known:
        review_strings.extend(known.review_strings)
    return _base_plan(
        row=row,
        canonical=canonical,
        source_family="twitter_x",
        record_type="post/status",
        platform_or_provider="X/Twitter",
        bundle_id=f"bundle:twitter_x:post:{post_id}",
        root_output_path=root,
        expected_record_paths=(f"{root}/post.json", f"{root}/post.md", f"{root}/records.ndjson", f"{root}/review_strings.txt", f"{root}/source_role_bridge.json"),
        expected_child_paths=(
            PlannedChildPath("media", f"{root}/media/", "planned post media folder"),
            PlannedChildPath("comments", f"{root}/comments/", "planned comments folder"),
            PlannedChildPath("replies", f"{root}/replies/", "planned replies folder"),
        ),
        expected_media_candidate_ids=(media_id,),
        review_strings=review_strings,
        capture_method_id="extension_manual_receipt_or_local_exporter_import_contract",
        allowed_methods=("extension_manual_receipt_import", "local_exporter_import", "webview2_visible_browser_observed"),
        requires_human_chain=True,
        requires_manual_receipt=True,
    )


def build_twitter_timeline_plan(row: SourceRowInput, canonical: str, handle: str, capture_timestamp: str) -> EvidenceBundlePlan:
    known = build_twitter_timeline_record() if canonical == "https://x.com/examaddaorg" else None
    root = f"source_exports/twitter_x/{_safe_segment(handle, 'account')}/capture_{capture_timestamp}"
    media_id = build_twitter_sample_media_candidate().candidate_id if canonical == "https://x.com/examaddaorg" else f"media:twitter_x:{handle}:dynamic_placeholder"
    review_strings = [
        canonical,
        f"twitter_x:timeline:{handle}",
        handle,
        f"@{handle}",
        "timeline.ndjson",
        "progress_events.ndjson",
        "posts/<post_id>/",
    ]
    if known:
        review_strings.extend(known.review_strings)
    return _base_plan(
        row=row,
        canonical=canonical,
        source_family="twitter_x",
        record_type="timeline/account_export",
        platform_or_provider="X/Twitter",
        bundle_id=f"bundle:twitter_x:timeline:{handle}",
        root_output_path=root,
        expected_record_paths=(f"{root}/manifest.json", f"{root}/timeline.md", f"{root}/timeline.ndjson", f"{root}/records.ndjson", f"{root}/review_strings.txt", f"{root}/media_index.json", f"{root}/progress_events.ndjson", f"{root}/audit_log.ndjson"),
        expected_child_paths=(PlannedChildPath("posts", f"{root}/posts/<post_id>/", "planned post bundle folders"),),
        expected_media_candidate_ids=(media_id,),
        review_strings=review_strings,
        capture_method_id="dynamic_gradual_discovery_receipt_contract",
        allowed_methods=("extension_manual_receipt_import", "local_exporter_import", "webview2_visible_browser_observed"),
        requires_human_chain=True,
    )


def build_news_article_plan(row: SourceRowInput, canonical: str, capture_timestamp: str) -> EvidenceBundlePlan:
    record = build_news_article_record() if "metro.co.uk/2026/07/17/people-shout-seagull-eater" in canonical else None
    host = urlsplit(canonical).netloc.lower().removeprefix("www.") or "site"
    root = f"source_exports/news_websites/{host}/capture_{capture_timestamp}"
    media_id = build_generic_article_sample_media_candidate().candidate_id
    bundle_id = "bundle:news_websites:article:metro_seagull_eater_20260717" if record else f"bundle:news_websites:article:{_fingerprint([canonical])}"
    review_strings = [canonical, host, "article.json", "article.md", "comments/", "screenshots/", "archive/", media_id]
    if record:
        review_strings.extend(record.review_strings)
    return _base_plan(
        row=row,
        canonical=canonical,
        source_family="news_websites",
        record_type="article",
        platform_or_provider="Metro" if "metro.co.uk" in host else host,
        bundle_id=bundle_id,
        root_output_path=root,
        expected_record_paths=(f"{root}/manifest.json", f"{root}/article.json", f"{root}/article.md", f"{root}/records.ndjson", f"{root}/review_strings.txt", f"{root}/media_index.json"),
        expected_child_paths=(
            PlannedChildPath("comments", f"{root}/comments/", "planned article comments folder"),
            PlannedChildPath("screenshots", f"{root}/screenshots/", "planned rendered screenshot folder"),
            PlannedChildPath("archive", f"{root}/archive/", "planned archive metadata folder"),
        ),
        expected_media_candidate_ids=(media_id,),
        review_strings=review_strings,
        capture_method_id="generic_article_lane_contract",
        allowed_methods=("api3128_jdownloader", "webview2_visible_browser_observed", "manual_user_selected_media"),
        access_status=STATUS_METADATA_ONLY_UNTIL_CAPTURED,
    )


def build_public_audio_plan(row: SourceRowInput, canonical: str, capture_timestamp: str) -> EvidenceBundlePlan:
    record = build_global_player_audio_record()
    root = f"source_exports/public_broadcast_catchup_audio/lbc/capture_{capture_timestamp}"
    media_id = build_global_player_media_candidate().candidate_id
    review_strings = list(record.review_strings) + [
        canonical,
        "2zGwFmzE7xNLAfiMVL5BMHmPeB",
        "media/original.m4a",
        "sidecars/info.json",
        "sidecars/description.txt",
        "sidecars/thumbnail.*",
        str(GLOBAL_PLAYER_METHOD_METADATA["preferred_invocation"]),
        str(GLOBAL_PLAYER_METHOD_METADATA["native_format_id_observed"]),
        str(GLOBAL_PLAYER_METHOD_METADATA["native_container"]),
        "preserve_native_m4a_no_conversion",
    ]
    return _base_plan(
        row=row,
        canonical=canonical,
        source_family="public_broadcast_catchup_audio",
        record_type="episode/audio_item",
        platform_or_provider="Global Player",
        bundle_id="bundle:public_broadcast_catchup_audio:episode:2zGwFmzE7xNLAfiMVL5BMHmPeB",
        root_output_path=root,
        expected_record_paths=(f"{root}/manifest.json", f"{root}/episode.json", f"{root}/episode.md", f"{root}/records.ndjson", f"{root}/review_strings.txt", f"{root}/media_index.json"),
        expected_child_paths=(
            PlannedChildPath("media", f"{root}/media/original.m4a", "planned native M4A preservation path"),
            PlannedChildPath("sidecar", f"{root}/sidecars/info.json", "planned yt-dlp info JSON sidecar"),
            PlannedChildPath("sidecar", f"{root}/sidecars/description.txt", "planned description sidecar"),
            PlannedChildPath("sidecar", f"{root}/sidecars/thumbnail.*", "planned thumbnail sidecar"),
        ),
        expected_media_candidate_ids=(media_id,),
        review_strings=review_strings,
        capture_method_id="yt_dlp_python_module",
        allowed_methods=("yt_dlp_python_module", "manual_user_selected_media", "local_file_import"),
        access_status=STATUS_REVIEW_REQUIRED,
    )


def build_unknown_or_blocked_plan(row: SourceRowInput, canonical: str, family: str, capture_timestamp: str, *, blocked_reason: str) -> EvidenceBundlePlan:
    safe_family = _safe_segment(family or "unknown", "unknown")
    root = f"source_exports/{safe_family}/review_only/capture_{capture_timestamp}/{_fingerprint([canonical, row.row_id])}"
    status = STATUS_PROHIBITED_NO_BYPASS if any(token in blocked_reason for token in ("private", "login", "prohibited", "blocked")) else STATUS_REVIEW_REQUIRED
    return _base_plan(
        row=row,
        canonical=canonical,
        source_family=family or "unknown",
        record_type="unknown_source_row",
        platform_or_provider=family or "unknown",
        bundle_id=f"bundle:{safe_family}:review_only:{_fingerprint([canonical, row.row_id])}",
        root_output_path=root,
        expected_record_paths=(f"{root}/manifest.json", f"{root}/records.ndjson", f"{root}/review_strings.txt", f"{root}/source_role_bridge.json"),
        expected_child_paths=(),
        expected_media_candidate_ids=(),
        review_strings=(canonical, row.source_title, row.source_label, row.source_candidate_id, blocked_reason),
        capture_method_id="review_only_no_capture_route",
        allowed_methods=("manual_receipt_import",) if status == STATUS_REVIEW_REQUIRED else (),
        blocked_methods=("network_fetch", "live_browser", "yt_dlp", "jdownloader", "extension_execution", "archive_submission"),
        access_status=status,
        review_status=STATUS_REVIEW_REQUIRED,
        requires_login="login" in blocked_reason,
        blocked_reason=blocked_reason,
    )


def build_planned_source_role_bridge(plan: EvidenceBundlePlan) -> PlannedSourceRoleBridge:
    return PlannedSourceRoleBridge(
        bridge_id=f"bridge:{plan.bundle_id}",
        bundle_id=plan.bundle_id,
        evidence_id=plan.bundle_id.removeprefix("bundle:"),
        source_candidate_id=plan.source_candidate_id,
        source_family=plan.source_family,
        candidate_kind=plan.record_type,
        review_strings=_record_review_strings(plan),
        blocked_reason=plan.blocked_reason,
    )


def build_review_string_index_link(plan: EvidenceBundlePlan) -> Mapping[str, Any]:
    return {
        "bundle_id": plan.bundle_id,
        "plan_id": plan.plan_id,
        "review_strings_path": plan.review_strings_path,
        "review_strings": [item.to_dict() for item in plan.review_strings],
        "records_by_string": {item.value: [plan.bundle_id] for item in plan.review_strings},
        "source_role_bridge_path": plan.source_role_bridge_path,
        "source_role_bridge_status": plan.source_role_bridge_status,
    }


def sample_source_rows() -> tuple[SourceRowInput, ...]:
    return (
        SourceRowInput(row_id="row_bbc_post", raw_input="https://x.com/BBCr4today/status/2097217541416308845?s=20", source_title="BBC Radio 4 Today post", source_candidate_id="candidate:bbc_post", selected_for_capture=True),
        SourceRowInput(row_id="row_examaddaorg", raw_input="https://x.com/examaddaorg?utm_source=test&s=20", source_title="examaddaorg timeline", source_candidate_id="candidate:examaddaorg", selected_for_capture=True),
        SourceRowInput(row_id="row_metro_article", raw_input="https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/", source_title="Metro article", source_candidate_id="candidate:metro_article", selected_for_capture=True),
        SourceRowInput(row_id="row_global_player", raw_input="https://www.globalplayer.com/catchup/lbc/uk/episodes/2zGwFmzE7xNLAfiMVL5BMHmPeB/", source_title="Global Player LBC episode", source_candidate_id="candidate:global_player_lbc", selected_for_capture=True),
        SourceRowInput(row_id="row_private", raw_input="https://private.example.local/protected", source_family_hint="unknown", capture_mode_hint="private login blocked", source_candidate_id="candidate:private", selected_for_capture=False, requires_review=True),
    )


def sample_plans() -> tuple[EvidenceBundlePlan, ...]:
    return tuple(build_evidence_bundle_plan_from_source_row(row) for row in sample_source_rows())


def machine_url_fields_are_plain(value: Any, key: str = "") -> bool:
    if isinstance(value, Mapping):
        return all(machine_url_fields_are_plain(item, child_key) for child_key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(machine_url_fields_are_plain(item, key) for item in value)
    if key in MACHINE_URL_FIELDS:
        text = str(value or "").strip()
        return not text.startswith("[") and "](" not in text
    return True


def url_like_review_strings_are_plain(plans: Sequence[EvidenceBundlePlan]) -> bool:
    for plan in plans:
        for item in plan.review_strings:
            text = item.value.strip()
            if re.match(r"(?i)^https?://", text) and (text.startswith("[") or "](" in text):
                return False
    return True


def build_evidence_bundle_plan_report(source_root: str | Path = ".") -> R42GKReport:
    plans = sample_plans()
    bridges = tuple(build_planned_source_role_bridge(plan) for plan in plans)
    index_links = tuple(build_review_string_index_link(plan) for plan in plans)
    r42gg = validate_universal_source_map(source_root)
    r42gh = validate_source_map_raw_url_audio_catchup(source_root)
    r42gi = validate_universal_media_method_matrix(source_root)
    r42gj = build_r42gj_report(source_root)
    all_payloads: list[Any] = [plan.to_dict() for plan in plans]
    checks = (
        _check("source_row_input_schema_complete", set(SOURCE_ROW_INPUT_SCHEMA_FIELDS).issubset(set(SourceRowInput.__dataclass_fields__))),
        _check("evidence_bundle_plan_schema_complete", set(EVIDENCE_BUNDLE_PLAN_SCHEMA_FIELDS).issubset(set(EvidenceBundlePlan.__dataclass_fields__))),
        _check("twitter_single_post_plan_present", any(plan.bundle_id == "bundle:twitter_x:post:2097217541416308845" and "BBC Radio 4 Today" in _record_review_strings(plan) for plan in plans)),
        _check("twitter_timeline_context_only", any(plan.bundle_id == "bundle:twitter_x:timeline:examaddaorg" and all("record_count=6700" not in item.value for item in plan.review_strings) for plan in plans)),
        _check("news_article_plan_present", any(plan.bundle_id == "bundle:news_websites:article:metro_seagull_eater_20260717" and any(path.kind == "archive" for path in plan.expected_child_paths) for plan in plans)),
        _check("public_audio_plan_preserves_r42gh_metadata", any(plan.bundle_id == "bundle:public_broadcast_catchup_audio:episode:2zGwFmzE7xNLAfiMVL5BMHmPeB" and "yt_dlp_python_module" == plan.capture_method_id and any("media/original.m4a" in path.path for path in plan.expected_child_paths) for plan in plans)),
        _check("unknown_private_review_only_plan_present", any(plan.record_type == "unknown_source_row" and plan.promotion_status == PROMOTION_NONE and plan.blocked_reason for plan in plans)),
        _check("r42gi_media_candidates_linkable_without_promotion", all(plan.promotion_status == PROMOTION_NONE for plan in plans) and any("media:public_broadcast_catchup_audio" in media_id for plan in plans for media_id in plan.expected_media_candidate_ids)),
        _check("plain_machine_urls_not_markdown", all(machine_url_fields_are_plain(payload) for payload in all_payloads) and url_like_review_strings_are_plain(plans)),
        _check("source_role_bridge_guardrail", all(bridge.role_status == ROLE_STATUS_COMPAT and bridge.promotion_status == PROMOTION_NONE and bridge.no_jump_counter_safe for bridge in bridges)),
        _check("side_effect_boundary_declared", all(SIDE_EFFECT_BOUNDARY == plan.side_effect_boundary for plan in plans)),
        _check("prior_green_layers_import", r42gg.status == R42GG_PASS_STATUS and r42gh.status == R42GH_PASS_STATUS and r42gi.status == R42GI_PASS_STATUS and r42gj.status == R42GJ_PASS_STATUS, f"{r42gg.status} {r42gh.status} {r42gi.status} {r42gj.status}"),
    )
    status = R42GK_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GK_BLOCKED_STATUS
    return R42GKReport(
        marker=R42GK_MARKER,
        schema_version=R42GK_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_root=str(source_root),
        status=status,
        source_row_input_schema=_schema(SOURCE_ROW_INPUT_SCHEMA_FIELDS),
        evidence_bundle_plan_schema=_schema(EVIDENCE_BUNDLE_PLAN_SCHEMA_FIELDS),
        sample_plans=tuple(plan.to_dict() for plan in plans),
        sample_source_role_bridges=tuple(bridge.to_dict() for bridge in bridges),
        sample_review_string_index_links=tuple(dict(link) for link in index_links),
        checks=checks,
    )


def validate_evidence_bundle_plan_report(source_root: str | Path = ".") -> R42GKReport:
    return build_evidence_bundle_plan_report(source_root)


def _report_markdown(report: R42GKReport) -> str:
    lines = [
        "# R42GK Source Row to Evidence Bundle Plan Bridge",
        "",
        f"Marker: `{report.marker}`",
        f"Status: `{report.status}`",
        f"Schema version: `{report.schema_version}`",
        "",
        "## Checks",
    ]
    for check in report.checks:
        detail = f" - {check['detail']}" if check.get("detail") else ""
        lines.append(f"- {check['name']}: {check['status']}{detail}")
    lines.extend(["", "## Side Effect Boundary", report.side_effect_boundary])
    return "\n".join(lines) + "\n"


def write_report(report: R42GKReport, output_root: str | Path) -> None:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    outputs = {
        "R42GK_SOURCE_ROW_EVIDENCE_BUNDLE_PLAN_REPORT.json": report.to_dict(),
        "R42GK_SOURCE_ROW_INPUT_SCHEMA.json": report.source_row_input_schema,
        "R42GK_EVIDENCE_BUNDLE_PLAN_SCHEMA.json": report.evidence_bundle_plan_schema,
        "R42GK_SAMPLE_PLANS.json": [dict(plan) for plan in report.sample_plans],
        "R42GK_SAMPLE_SOURCE_ROLE_BRIDGES.json": [dict(bridge) for bridge in report.sample_source_role_bridges],
        "R42GK_SAMPLE_REVIEW_STRING_INDEX_LINKS.json": [dict(link) for link in report.sample_review_string_index_links],
    }
    for filename, data in outputs.items():
        (root / filename).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    (root / "R42GK_SOURCE_ROW_EVIDENCE_BUNDLE_PLAN_REPORT.md").write_text(_report_markdown(report), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the R42GK source-row evidence bundle plan report.")
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-root", default=r"profile_media_live_captures\r42gk_source_row_evidence_bundle_plan")
    args = parser.parse_args(argv)
    report = build_evidence_bundle_plan_report(args.source_root)
    write_report(report, args.output_root)
    print(R42GK_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.status == R42GK_PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
