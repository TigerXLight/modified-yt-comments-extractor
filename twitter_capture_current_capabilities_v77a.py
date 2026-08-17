from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Mapping


TWITTER_CAPTURE_CAPABILITIES_SCHEMA_VERSION = "twitter_capture_current_capabilities.v77a"


@dataclass(frozen=True)
class TwitterCaptureCapabilityRow:
    capability: str
    status_tags: tuple[str, ...]
    implemented_files: tuple[str, ...]
    related_tests: tuple[str, ...]
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterCaptureCapabilityAudit:
    schema_version: str
    rows: tuple[TwitterCaptureCapabilityRow, ...]
    unsafe_out_of_scope_actions: tuple[str, ...]
    official_x_api_used: bool
    write_actions_implemented: bool
    browser_launch_performed_by_audit: bool
    web_download_performed_by_audit: bool
    media_download_performed_by_audit: bool
    external_reference_sources_vendored: bool

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


def build_twitter_capture_capability_audit() -> TwitterCaptureCapabilityAudit:
    rows = (
        TwitterCaptureCapabilityRow(
            capability="URL adapter and compact source row",
            status_tags=("IMPLEMENTED", "GUI_ONLY", "TESTED"),
            implemented_files=("source_adapters.py", "source_twitter_compact_row.py", "main.py"),
            related_tests=("source_adapters_test.py", "source_twitter_compact_row_test.py", "main_source_resource_ui_test.py"),
            notes="X/Twitter source declaration and Post/Thread intent state exist; live capture success is not implied.",
        ),
        TwitterCaptureCapabilityRow(
            capability="Read-only browser/session response capture",
            status_tags=("IMPLEMENTED", "CLI_ONLY", "PARTIAL", "TESTED"),
            implemented_files=("twitter_browser_capture_strategy.py", "twitter_browser_capture_runner.py", "twitter_browser_capture_inspector.py"),
            related_tests=("twitter_browser_capture_strategy_test.py", "twitter_browser_capture_runner_test.py", "twitter_browser_capture_inspector_test.py"),
            notes="Uses observed browser web responses and rendered DOM evidence. It is not the official X API.",
        ),
        TwitterCaptureCapabilityRow(
            capability="Timeline cursor continuation and cooldown state",
            status_tags=("IMPLEMENTED", "CLI_ONLY", "PARTIAL", "TESTED"),
            implemented_files=("twitter_browser_timeline_pagination.py", "twitter_timeline_cursor_scheduler.py", "twitter_rate_limit_policy.py"),
            related_tests=("twitter_reference_sources_test.py", "tools/assert_twitter_cursor_*.py"),
            notes="Cursor/page/rate-limit state is modelled; V77A adds deterministic continuation proof without live fetch.",
        ),
        TwitterCaptureCapabilityRow(
            capability="Rendered DOM fallback and status evidence",
            status_tags=("IMPLEMENTED", "PARTIAL", "TESTED"),
            implemented_files=("twitter_browser_capture_runner.py", "twitter_status_evidence_extractor.py"),
            related_tests=("twitter_browser_capture_runner_test.py",),
            notes="DOM fallback and status evidence sidecars exist; completeness remains review-bound.",
        ),
        TwitterCaptureCapabilityRow(
            capability="Screenshot/full-page preservation proof",
            status_tags=("IMPLEMENTED", "TESTED", "OFFLINE_PROOF"),
            implemented_files=("twitter_capture_screenshot_preservation.py",),
            related_tests=("twitter_capture_screenshot_preservation_test.py",),
            notes="Reimplements reference-family viewport stepping, overlap, edge handling, stable filenames, and manifest fields without launching a browser.",
        ),
        TwitterCaptureCapabilityRow(
            capability="Profile/Media provenance bridge",
            status_tags=("IMPLEMENTED", "TESTED", "REVIEW_REQUIRED"),
            implemented_files=("twitter_capture_profile_media_provenance.py", "profile_media_social_video_provenance.py"),
            related_tests=("twitter_capture_profile_media_provenance_test.py", "profile_media_social_video_provenance_test.py"),
            notes="Produces Profile/Media-compatible fields for screenshots/media/DOM/cursor records with final_source_role_decision=false.",
        ),
        TwitterCaptureCapabilityRow(
            capability="Shared media backend",
            status_tags=("IMPLEMENTED", "PARTIAL", "TESTED"),
            implemented_files=("twitter_media_backend.py", "source_media_execution_bridge.py"),
            related_tests=("twitter_media_backend_test.py",),
            notes="Media backend is shared and operator controlled. V77A tests do not download media.",
        ),
        TwitterCaptureCapabilityRow(
            capability="Full account export parity",
            status_tags=("NOT_IMPLEMENTED", "NEEDS_MANUAL_REVIEW"),
            implemented_files=(),
            related_tests=(),
            notes="External exporter references remain REFERENCE_ONLY; no bulk account export parity is claimed.",
        ),
    )
    return TwitterCaptureCapabilityAudit(
        schema_version=TWITTER_CAPTURE_CAPABILITIES_SCHEMA_VERSION,
        rows=rows,
        unsafe_out_of_scope_actions=("posting", "deleting", "liking", "following", "unfollowing", "direct_messages", "credential_automation", "captcha_bypass", "proxy_or_evasion", "aggressive_rate_limit_bypass"),
        official_x_api_used=False,
        write_actions_implemented=False,
        browser_launch_performed_by_audit=False,
        web_download_performed_by_audit=False,
        media_download_performed_by_audit=False,
        external_reference_sources_vendored=False,
    )


def render_twitter_capture_capability_audit_text(audit: TwitterCaptureCapabilityAudit | None = None) -> str:
    audit = audit or build_twitter_capture_capability_audit()
    lines = [
        "TWITTER/X CURRENT CAPABILITIES V77A",
        f"official_x_api_used: {audit.official_x_api_used}",
        f"write_actions_implemented: {audit.write_actions_implemented}",
        f"browser_launch_performed_by_audit: {audit.browser_launch_performed_by_audit}",
        f"web_download_performed_by_audit: {audit.web_download_performed_by_audit}",
        f"media_download_performed_by_audit: {audit.media_download_performed_by_audit}",
    ]
    for row in audit.rows:
        lines.append(f"- {row.capability}: {', '.join(row.status_tags)}")
    lines.append("unsafe_out_of_scope_actions: " + ", ".join(audit.unsafe_out_of_scope_actions))
    return "\n".join(lines)
