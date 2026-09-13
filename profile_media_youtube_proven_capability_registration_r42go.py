from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, unquote, urlsplit, urlunsplit

from profile_media_source_map_raw_url_audio_catchup_r42gh import R42GH_PASS_STATUS, validate_source_map_raw_url_audio_catchup
from profile_media_source_row_display_archive_audio_title_r42gn import R42GN_PASS_STATUS, validate_r42gn_source_row_display_archive_audio_title
from profile_media_source_row_evidence_bundle_plan_r42gk import PROMOTION_NONE, ROLE_STATUS_COMPAT, R42GK_PASS_STATUS, validate_evidence_bundle_plan_report
from profile_media_universal_evidence_bundle_index_r42gj import R42GJ_PASS_STATUS, build_report as build_r42gj_report
from profile_media_universal_media_method_matrix_r42gi import R42GI_PASS_STATUS, validate_universal_media_method_matrix
from profile_media_universal_source_map_r42gg import R42GG_PASS_STATUS, SIDE_EFFECT_BOUNDARY, sanitize_source_url, validate_universal_source_map
from source_adapters import find_source_method_profile
from source_resource_state import build_source_resource_row


R42GO_MARKER = "YTCE_R42GO_YOUTUBE_PROVEN_CAPABILITY_REGISTRATION_SOURCE_ROW_BOUNDARY_AUDIT"
R42GO_PASS_STATUS = "PASS_R42GO_YOUTUBE_PROVEN_CAPABILITY_REGISTRATION_SOURCE_ROW_BOUNDARY_AUDIT"
R42GO_BLOCKED_STATUS = "BLOCKED_R42GO_WITH_EXACT_BLOCKER"
R42GO_SCHEMA_VERSION = "youtube_proven_capability_registration.r42go.v1"

YOUTUBE_PROVEN_VIDEO_URL = "https://www.youtube.com/watch?v=qGNKkvxE61Q"
YOUTUBE_SOURCE_PROFILE_ID = "youtube_media_transcript_comment"
URL_MACHINE_FIELD_SUFFIXES = ("url", "path")

TEXT_DATA_REFERENCE_METRICS: Mapping[str, Any] = {
    "source_reference_pack": "YTCE_HANDOVER_CURRENT_WORKING_MODELS_20260913(1).zip",
    "test_video_id": "qGNKkvxE61Q",
    "youtubeButtonsClicked": 0,
    "initialCommentsWakeScrolls": 1,
    "seedTopLevelTokens": 3,
    "seedReplyTokens": 16,
    "continuationRequests": 305,
    "continuationResponses": 305,
    "continuationErrors": 0,
    "records": 685,
    "topLevelRecords": 365,
    "replyRecords": 320,
    "maxDepthObserved": 6,
    "recordsWithFullText": 685,
    "recordsWithAuthor": 685,
    "recordsWithRootId": 685,
    "elapsed_seconds": 8.001,
}

VISUAL_REFERENCE_METRICS: Mapping[str, Any] = {
    "source_reference_pack": "YTCE_HANDOVER_CURRENT_WORKING_MODELS_20260913(1).zip",
    "correctness_baseline": "R16_PROVEN_REPLIES_FAST_LOADER",
    "fast_model": "R17_ROOT_LOCAL_FAST",
    "r17_rendered_reply_openers": 0,
    "r17_rendered_read_more_buttons": 0,
    "r17_capture_gate": True,
    "r17_total_time": "1:26",
    "screenshot_engine_reference": "R2 viewport tile/stitch primitive",
    "obsolete_not_restored": "old R2 comment/reply expansion loop",
}

INSPECTED_FILES: tuple[str, ...] = (
    "main.py",
    "source_resource_state.py",
    "source_resource_state_test.py",
    "source_adapters.py",
    "source_adapters_test.py",
    "source_reference_intake.py",
    "source_reference_intake_test.py",
    "profile_media_source_package_preview.py",
    "profile_media_source_package_preview_test.py",
    "profile_media_source_intake.py",
    "profile_media_source_intake_test.py",
    "profile_media_preview_surface_integration_r42gm.py",
    "profile_media_existing_source_intake_bundle_preview_r42gl.py",
    "profile_media_source_row_evidence_bundle_plan_r42gk.py",
    "profile_media_universal_evidence_bundle_index_r42gj.py",
    "capture_controller.py",
    "capture_controller_test.py",
    "source_msn_comments_profile_export.py",
    "source_msn_comments_profile_export_test.py",
    "evidence_exporter.py",
)

LIVE_SOURCE_SYMBOLS: Mapping[str, tuple[str, ...]] = {
    "profile_media_source_package_preview.py": (
        "_parse_preserved_youtube_comment_records",
        "extract_preserved_youtube_comment_threads",
        "format_youtube_comment_threads_for_review_display",
        "_youtube_comment_source_role_records_from_review_sections",
        "preserved_youtube_comments",
    ),
    "source_adapters.py": (
        "YouTubeSourceAdapter",
        "youtube_media_transcript_comment",
        "supports_author_channel_ids=True",
        "supports_replies=True",
        "comments_tested=True",
    ),
    "source_resource_state.py": (
        "webpage_screenshot_requested",
        "comments_screenshot_requested",
        "livechat_screenshot_requested",
        "Comments supported by existing YouTube runtime elsewhere.",
    ),
    "capture_controller.py": (
        "youtube_media_transcript",
        "youtube_comments",
    ),
    "main.py": (
        "YouTubeCommentExtractor",
        "def _fetch_thread",
        "def attach_screenshots",
        "def export_evidence_folder",
        "def _append_youtube_metadata_to_source_info",
    ),
    "evidence_exporter.py": (
        "YouTube Comments - Readable Evidence Export",
        "Parent Comment",
        "Reply",
        "Screenshots are user-attached evidence files.",
    ),
    "source_msn_comments_profile_export.py": (
        "render_msn_comments_html",
        "searchBox",
        "author_profile_url",
        "profiles_csv_path",
        "profiles_html_path",
    ),
}


@dataclass(frozen=True)
class YoutubeCapabilityRegistration:
    capability_id: str
    source_family: str
    method_slot: str
    evidence_path: str
    proven_status: str
    source_row_adapter_id: str
    source_profile_id: str
    expected_artifacts: tuple[str, ...]
    review_string_kinds: tuple[str, ...]
    dependency_boundary: str
    source_role_bridge_status: str = ROLE_STATUS_COMPAT
    promotion_status: str = PROMOTION_NONE
    role_assignment_performed: bool = False
    capture_executed_by_r42go: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MsnComparisonRow:
    capability_area: str
    youtube_current_state: str
    msn_reference_strength: str
    safe_future_convergence: str
    replaces_youtube_format: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class R42GOReport:
    marker: str
    schema_version: str
    generated_at: str
    source_root: str
    status: str
    inspected_files: tuple[str, ...]
    live_source_inventory: Mapping[str, Any]
    registrations: tuple[Mapping[str, Any], ...]
    msn_comparison: tuple[Mapping[str, Any], ...]
    source_row_summary: Mapping[str, Any]
    source_method_profile_summary: Mapping[str, Any]
    checks: tuple[Mapping[str, str], ...]
    side_effect_boundary: str = SIDE_EFFECT_BOUNDARY

    @property
    def passed(self) -> bool:
        return self.status == R42GO_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "marker": self.marker,
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "source_root": self.source_root,
            "status": self.status,
            "passed": self.passed,
            "inspected_files": list(self.inspected_files),
            "live_source_inventory": dict(self.live_source_inventory),
            "registrations": [dict(item) for item in self.registrations],
            "msn_comparison": [dict(item) for item in self.msn_comparison],
            "source_row_summary": dict(self.source_row_summary),
            "source_method_profile_summary": dict(self.source_method_profile_summary),
            "checks": [dict(item) for item in self.checks],
            "side_effect_boundary": self.side_effect_boundary,
        }


def _check(name: str, condition: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _read_text(root: str | Path, relative_path: str) -> str:
    path = Path(root) / relative_path
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def build_live_source_inventory(source_root: str | Path = ".") -> dict[str, Any]:
    """Inspect existing files for protected YouTube/MSN capability symbols."""

    files: dict[str, dict[str, Any]] = {}
    for relative_path, required_symbols in LIVE_SOURCE_SYMBOLS.items():
        text = _read_text(source_root, relative_path)
        present = tuple(symbol for symbol in required_symbols if symbol in text)
        files[relative_path] = {
            "exists": bool(text),
            "required_symbols": list(required_symbols),
            "present_symbols": list(present),
            "all_required_symbols_present": len(present) == len(required_symbols),
        }
    return {
        "files": files,
        "all_required_symbols_present": all(item["all_required_symbols_present"] for item in files.values()),
        "inspection_mode": "static_file_symbol_audit_no_runtime_engine_import",
    }


def build_youtube_capability_registrations() -> tuple[YoutubeCapabilityRegistration, ...]:
    """Register proven YouTube layers without starting or changing the engines."""

    return (
        YoutubeCapabilityRegistration(
            capability_id="comment_text_capture_proven",
            source_family="youtube",
            method_slot="youtube_comments_text_data_existing_runtime",
            evidence_path="text_data_path",
            proven_status="proven_by_current_working_models_r2_direct_continuation",
            source_row_adapter_id="youtube",
            source_profile_id=YOUTUBE_SOURCE_PROFILE_ID,
            expected_artifacts=("comments_jsonl", "comments_readable_txt", "comments_csv", "review_strings"),
            review_string_kinds=("canonical_url", "video_id", "comment_id", "author", "text_snippet", "thread_id"),
            dependency_boundary="does_not_depend_on_screenshot_expansion",
        ),
        YoutubeCapabilityRegistration(
            capability_id="comment_metadata_capture_proven",
            source_family="youtube",
            method_slot="youtube_comment_metadata_existing_runtime",
            evidence_path="text_data_path",
            proven_status="proven_by_current_working_models_r2_direct_continuation",
            source_row_adapter_id="youtube",
            source_profile_id=YOUTUBE_SOURCE_PROFILE_ID,
            expected_artifacts=("author", "published_at", "likes", "parent_id", "thread_id", "depth", "root_id"),
            review_string_kinds=("author", "created_at_text", "stats_text", "parent_id", "root_id"),
            dependency_boundary="metadata_is_text_data_path_not_visual_path",
        ),
        YoutubeCapabilityRegistration(
            capability_id="reply_thread_level_indentation_format_proven",
            source_family="youtube",
            method_slot="youtube_readable_export_thread_indentation",
            evidence_path="review_text_export_path",
            proven_status="proven_by_profile_media_source_package_preview_and_evidence_exporter",
            source_row_adapter_id="youtube",
            source_profile_id=YOUTUBE_SOURCE_PROFILE_ID,
            expected_artifacts=("comments_readable.txt", "review_transcript_box_text", "preserved_youtube_comments"),
            review_string_kinds=("author_handle", "time_label", "indented_reply_text", "parent_context"),
            dependency_boundary="preserves_notepad_readable_reply_indentation",
        ),
        YoutubeCapabilityRegistration(
            capability_id="screenshot_capture_proven",
            source_family="youtube",
            method_slot="youtube_visual_screenshot_existing_runtime",
            evidence_path="visual_screenshot_path",
            proven_status="proven_by_current_working_models_r16_r17_plus_r2_screenshot_engine",
            source_row_adapter_id="youtube",
            source_profile_id=YOUTUBE_SOURCE_PROFILE_ID,
            expected_artifacts=("page_screenshot_png", "attached_screenshots", "source_info_screenshot_count"),
            review_string_kinds=("source_url", "screenshot_relative_path", "capture_state"),
            dependency_boundary="visual_path_separate_from_fast_text_data_path",
        ),
        YoutubeCapabilityRegistration(
            capability_id="visual_expansion_path_proven",
            source_family="youtube",
            method_slot="youtube_visible_comment_expansion_existing_runtime",
            evidence_path="visual_screenshot_path",
            proven_status="proven_by_r16_correctness_and_r17_fast_model_reference",
            source_row_adapter_id="youtube",
            source_profile_id=YOUTUBE_SOURCE_PROFILE_ID,
            expected_artifacts=("expanded_visible_comment_state", "capture_gate_state", "visual_audit_log"),
            review_string_kinds=("video_id", "expansion_state", "capture_gate"),
            dependency_boundary="visual_expansion_not_required_for_text_continuation_capture",
        ),
        YoutubeCapabilityRegistration(
            capability_id="screenshot_tile_or_viewport_stitch_evidence_proven",
            source_family="youtube",
            method_slot="youtube_viewport_tile_stitch_screenshot_evidence",
            evidence_path="visual_screenshot_path",
            proven_status="proven_by_r2_viewport_tile_stitch_reference",
            source_row_adapter_id="youtube",
            source_profile_id=YOUTUBE_SOURCE_PROFILE_ID,
            expected_artifacts=("viewport_tiles", "stitched_or_segmented_png", "tile_y_positions"),
            review_string_kinds=("tile_path", "stitched_image_path", "viewport_range"),
            dependency_boundary="screenshot_materialization_separate_from_comment_text_export",
        ),
        YoutubeCapabilityRegistration(
            capability_id="optional_author_profile_url_export",
            source_family="youtube",
            method_slot="youtube_optional_author_channel_profile_url_export",
            evidence_path="optional_profile_url_path",
            proven_status="supported_by_adapter_capability_and_msn_v35_pattern_optional_not_forced",
            source_row_adapter_id="youtube",
            source_profile_id=YOUTUBE_SOURCE_PROFILE_ID,
            expected_artifacts=("author_channel_id", "author_channel_url_optional", "profile_url_sidecar_optional"),
            review_string_kinds=("author", "author_channel_id", "author_channel_url"),
            dependency_boundary="optional_export_flag_not_forced_by_r42go",
        ),
        YoutubeCapabilityRegistration(
            capability_id="searchable_html_export_capability",
            source_family="youtube",
            method_slot="youtube_searchable_html_export_future_optional",
            evidence_path="optional_searchable_html_path",
            proven_status="future_optional_pattern_from_msn_v34_not_engine_change",
            source_row_adapter_id="youtube",
            source_profile_id=YOUTUBE_SOURCE_PROFILE_ID,
            expected_artifacts=("searchable_comments_html_optional", "copy_results_optional", "download_search_txt_optional"),
            review_string_kinds=("comment_text", "author", "profile_url_optional"),
            dependency_boundary="registration_only_does_not_replace_existing_youtube_text_format",
        ),
        YoutubeCapabilityRegistration(
            capability_id="no_engine_changes",
            source_family="youtube",
            method_slot="registration_audit_only",
            evidence_path="source_row_method_evidence_bundle_bridge",
            proven_status="r42go_does_not_execute_or_modify_capture_engines",
            source_row_adapter_id="youtube",
            source_profile_id=YOUTUBE_SOURCE_PROFILE_ID,
            expected_artifacts=("registration_report", "audit_notes", "green_state_zip"),
            review_string_kinds=("capability_id", "method_slot", "source_profile_id"),
            dependency_boundary="no_live_capture_no_browser_no_download_no_source_role_assignment",
        ),
    )


def build_msn_comparison_table() -> tuple[MsnComparisonRow, ...]:
    return (
        MsnComparisonRow(
            capability_area="comment_text_export_readability",
            youtube_current_state="Existing YouTube readable export keeps parent/reply labels and indentation for Notepad-friendly review.",
            msn_reference_strength="V34/V35 comments TXT/MD/HTML also preserve nested readability and deleted placeholders.",
            safe_future_convergence="Keep YouTube indentation format; only borrow optional search/export ergonomics.",
        ),
        MsnComparisonRow(
            capability_area="searchable_html_output",
            youtube_current_state="No forced R42GO YouTube HTML export change; existing readable TXT/CSV/package path remains protected.",
            msn_reference_strength="V34 HTML includes searchBox, additional-info toggle, Copy results, Download search TXT/JSON, and visible export box.",
            safe_future_convergence="Add optional YouTube searchable HTML export later without replacing TXT indentation.",
        ),
        MsnComparisonRow(
            capability_area="author_profile_or_channel_url",
            youtube_current_state="YouTube adapter declares author channel IDs; R42GO registers profile/channel URL export as optional, not forced.",
            msn_reference_strength="V35 profile URL/account sidecars normalize author_profile_url, profile CID, account stats, and sidecar files.",
            safe_future_convergence="Model optional per-comment YouTube author channel URL sidecars after MSN V35 without changing capture defaults.",
        ),
        MsnComparisonRow(
            capability_area="visual_screenshot_evidence",
            youtube_current_state="Existing screenshot path is separate user-attached/visual evidence; text/data path does not depend on it.",
            msn_reference_strength="MSN references are comment/export sidecars rather than YouTube visual expansion replacements.",
            safe_future_convergence="Keep YouTube visual capture route independent from text/data capture.",
        ),
    )


def _source_row_summary() -> dict[str, Any]:
    row = build_source_resource_row(YOUTUBE_PROVEN_VIDEO_URL)
    raw_url = _plain_machine_url(row.raw_url)
    canonical_url = _plain_machine_url(row.canonical_url)
    return {
        "row_id": row.row_id,
        "adapter_id": row.adapter_id,
        "raw_url": raw_url,
        "canonical_url": canonical_url,
        "comments_supported": row.comments_supported,
        "livechat_supported": row.livechat_supported,
        "comments_status": row.comments_status,
        "livechat_status": row.livechat_status,
        "provenance": row.provenance,
        "source_roles_or_counters_mutated": False,
    }


def _plain_machine_url(value: Any) -> str:
    """Return a URL-like machine field without Markdown link wrapping."""

    text = str(value or "").strip()
    if not text:
        return ""
    # Handle pasted Markdown links such as [label](https://example.test/a)
    # and bare Markdown-wrapped URLs such as [https://x](https://x).
    if "](" in text:
        candidate = text.split("](", 1)[1].split(")", 1)[0].strip()
        text = candidate or text
    elif text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    text = unquote(text).replace("\\_", "_").replace("\\", "")
    sanitized = sanitize_source_url(text)
    return _normalise_youtube_machine_url(sanitized or text)


def _normalise_youtube_machine_url(value: str) -> str:
    parsed = urlsplit(value)
    host = parsed.netloc.lower()
    if host not in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        return value
    query_pairs = []
    for key, item in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered == "v" or lowered in {"t", "start"}:
            query_pairs.append((key, item))
    query = urlencode(query_pairs)
    return urlunsplit((parsed.scheme or "https", "www.youtube.com", parsed.path or "/watch", query, ""))


def _is_plain_machine_url(value: Any) -> bool:
    text = str(value or "").strip()
    return not text.startswith("[") and "](" not in text and r"]\(" not in text


def source_row_summary_url_fields_are_plain(summary: Mapping[str, Any]) -> bool:
    for key, value in summary.items():
        lowered = str(key).lower()
        if lowered.endswith(URL_MACHINE_FIELD_SUFFIXES) or "url" in lowered:
            if not _is_plain_machine_url(value):
                return False
    return True


def _source_method_profile_summary() -> dict[str, Any]:
    profile = find_source_method_profile(YOUTUBE_SOURCE_PROFILE_ID)
    return {
        "profile_id": profile.profile_id,
        "adapter_id": profile.adapter_id,
        "method_family": profile.method_family,
        "supported_modes": tuple(profile.supported_modes),
        "expected_artifact_types": tuple(profile.expected_artifact_types),
        "notes": profile.notes,
    }


def _string_values_plain(value: Any) -> bool:
    if isinstance(value, Mapping):
        return all(_string_values_plain(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_string_values_plain(item) for item in value)
    if isinstance(value, str) and ("http://" in value or "https://" in value):
        return _is_plain_machine_url(value)
    return True


def build_youtube_proven_capability_registration_report(source_root: str | Path = ".") -> R42GOReport:
    inventory = build_live_source_inventory(source_root)
    registrations = build_youtube_capability_registrations()
    registration_payloads = tuple(item.to_dict() for item in registrations)
    comparison = tuple(item.to_dict() for item in build_msn_comparison_table())
    row_summary = _source_row_summary()
    profile_summary = _source_method_profile_summary()

    r42gg = validate_universal_source_map(source_root)
    r42gh = validate_source_map_raw_url_audio_catchup(source_root)
    r42gi = validate_universal_media_method_matrix(source_root)
    r42gj = build_r42gj_report(source_root)
    r42gk = validate_evidence_bundle_plan_report(source_root)
    r42gn = validate_r42gn_source_row_display_archive_audio_title()

    capability_ids = {item.capability_id for item in registrations}
    method_slots = {item.method_slot for item in registrations}
    checks = (
        _check("live_repo_symbols_found", bool(inventory["all_required_symbols_present"]), "static symbol inspection only"),
        _check("youtube_source_row_detected", row_summary["adapter_id"] == "youtube" and row_summary["comments_supported"] is True),
        _check("youtube_method_profile_present", profile_summary["profile_id"] == YOUTUBE_SOURCE_PROFILE_ID and profile_summary["adapter_id"] == "youtube"),
        _check("text_and_visual_paths_separate", "youtube_comments_text_data_existing_runtime" in method_slots and "youtube_visual_screenshot_existing_runtime" in method_slots),
        _check("text_capture_not_dependent_on_screenshot", any(item.capability_id == "comment_text_capture_proven" and "does_not_depend" in item.dependency_boundary for item in registrations)),
        _check("thread_indentation_registered", "reply_thread_level_indentation_format_proven" in capability_ids),
        _check("screenshot_tile_or_viewport_registered", "screenshot_tile_or_viewport_stitch_evidence_proven" in capability_ids),
        _check("optional_author_profile_url_not_forced", any(item.capability_id == "optional_author_profile_url_export" and "optional" in item.method_slot for item in registrations)),
        _check("searchable_html_future_optional_not_engine_change", any(item.capability_id == "searchable_html_export_capability" and "future_optional" in item.method_slot for item in registrations)),
        _check("msn_contrast_does_not_replace_youtube", all(item["replaces_youtube_format"] is False for item in comparison)),
        _check("source_role_bridge_compatible_only", all(item.source_role_bridge_status == ROLE_STATUS_COMPAT and item.role_assignment_performed is False for item in registrations)),
        _check("promotion_status_non_promoting", all(item.promotion_status == PROMOTION_NONE for item in registrations)),
        _check("plain_url_and_review_strings", _string_values_plain(registration_payloads) and _string_values_plain(row_summary) and source_row_summary_url_fields_are_plain(row_summary)),
        _check("side_effects_not_run", all(item.capture_executed_by_r42go is False for item in registrations) and "no network fetch" in SIDE_EFFECT_BOUNDARY.lower()),
        _check("r42gg_to_r42gn_green_layers_import", r42gg.status == R42GG_PASS_STATUS and r42gh.status == R42GH_PASS_STATUS and r42gi.status == R42GI_PASS_STATUS and r42gj.status == R42GJ_PASS_STATUS and r42gk.status == R42GK_PASS_STATUS and r42gn["status"] == R42GN_PASS_STATUS, f"{r42gg.status} {r42gh.status} {r42gi.status} {r42gj.status} {r42gk.status} {r42gn['status']}"),
        _check("canonical_youtube_url_plain", sanitize_source_url(YOUTUBE_PROVEN_VIDEO_URL).startswith("https://") and "qGNKkvxE61Q" in sanitize_source_url(YOUTUBE_PROVEN_VIDEO_URL) and not sanitize_source_url(YOUTUBE_PROVEN_VIDEO_URL).startswith("[")),
    )
    status = R42GO_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GO_BLOCKED_STATUS
    return R42GOReport(
        marker=R42GO_MARKER,
        schema_version=R42GO_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_root=str(source_root),
        status=status,
        inspected_files=INSPECTED_FILES,
        live_source_inventory=inventory,
        registrations=registration_payloads,
        msn_comparison=comparison,
        source_row_summary=row_summary,
        source_method_profile_summary=profile_summary,
        checks=checks,
    )


def validate_youtube_proven_capability_registration(source_root: str | Path = ".") -> R42GOReport:
    return build_youtube_proven_capability_registration_report(source_root)


def _report_markdown(report: R42GOReport) -> str:
    lines = [
        "# R42GO YouTube Proven Capability Registration / Source Row Boundary Audit",
        "",
        f"Marker: `{report.marker}`",
        f"Status: `{report.status}`",
        f"Schema version: `{report.schema_version}`",
        "",
        "## Registered Capabilities",
    ]
    for item in report.registrations:
        lines.append(
            f"- `{item['capability_id']}`: `{item['method_slot']}`; "
            f"path `{item['evidence_path']}`; status `{item['proven_status']}`"
        )
    lines.extend(["", "## MSN Comparison"])
    for item in report.msn_comparison:
        lines.append(f"- `{item['capability_area']}`: {item['safe_future_convergence']}")
    lines.extend(["", "## Checks"])
    for check in report.checks:
        detail = f" - {check['detail']}" if check.get("detail") else ""
        lines.append(f"- {check['name']}: {check['status']}{detail}")
    lines.extend(["", "## Side Effect Boundary", report.side_effect_boundary])
    return "\n".join(lines) + "\n"


def write_report(report: R42GOReport, output_root: str | Path) -> None:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "R42GO_YOUTUBE_PROVEN_CAPABILITY_REGISTRATION_REPORT.json").write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (root / "R42GO_YOUTUBE_PROVEN_CAPABILITY_REGISTRATION_REPORT.md").write_text(_report_markdown(report), encoding="utf-8")
    (root / "R42GO_YOUTUBE_CAPABILITY_REGISTRATIONS.json").write_text(
        json.dumps([dict(item) for item in report.registrations], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (root / "R42GO_MSN_CONTRAST_TABLE.json").write_text(
        json.dumps([dict(item) for item in report.msn_comparison], indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the R42GO YouTube capability registration report.")
    parser.add_argument("--source-root", default=".")
    parser.add_argument(
        "--output-root",
        default=r"profile_media_live_captures\r42go_youtube_proven_capability_registration_source_row_boundary_audit",
    )
    args = parser.parse_args(argv)
    report = build_youtube_proven_capability_registration_report(args.source_root)
    write_report(report, Path(args.source_root) / args.output_root)
    print(R42GO_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.status == R42GO_PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
