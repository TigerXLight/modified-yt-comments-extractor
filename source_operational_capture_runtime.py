from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


SOURCE_OPERATIONAL_CAPTURE_RUNTIME_SCHEMA_VERSION = "source_operational_capture_runtime_v1"


class OperationalResultStatus(str, Enum):
    PLANNED = "PLANNED"
    FIXTURE_TESTED = "FIXTURE_TESTED"
    LOCAL_MOCK_EXECUTED = "LOCAL_MOCK_EXECUTED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    NOT_LIVE_EXECUTED = "NOT_LIVE_EXECUTED"


UNSAFE_COMPLETION_STATUSES = {"COMPLETED_EVIDENCE", "LIVE_COMPLETE", "VERIFIED_EVIDENCE"}


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _stable_json(data: Any, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(_value_for_dict(data), indent=2, sort_keys=True)
    return json.dumps(_value_for_dict(data), sort_keys=True, separators=(",", ":"))


def _sha16(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


def _stable_tuple(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in values if str(value)}))


@dataclass(frozen=True)
class OperationalFixtureDescriptor:
    fixture_id: str
    category: str
    label: str
    expected_status: OperationalResultStatus = OperationalResultStatus.FIXTURE_TESTED
    source_method_refs: tuple[str, ...] = ()
    artifact_expectations: tuple[str, ...] = ()
    warning_flags: tuple[str, ...] = ()
    external_network_required: bool = False
    live_browser_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class OperationalCaptureRuntimeResult:
    capture_session_id: str
    source_url: str
    canonical_url: str
    access_mode: str
    capture_method: str
    selected_source_methods: tuple[str, ...]
    operator_approval_state: str
    started_at_utc: str
    finished_at_utc: str
    result_status: OperationalResultStatus
    artifact_references: tuple[str, ...] = ()
    receipt_references: tuple[str, ...] = ()
    warning_flags: tuple[str, ...] = ()
    completeness_flags: tuple[str, ...] = ()
    hash_chained_log_reference: str = ""
    no_live_execution: bool = True
    completed_evidence_claimed: bool = False
    verified_evidence_claimed: bool = False
    live_network_performed: bool = False
    browser_automation_performed: bool = False
    archive_provider_call_performed: bool = False
    download_performed: bool = False
    file_move_performed: bool = False
    raw_payload_included: bool = False
    schema_version: str = SOURCE_OPERATIONAL_CAPTURE_RUNTIME_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["result_id"] = "operational_capture_result_" + _sha16(
            {
                "capture_session_id": self.capture_session_id,
                "canonical_url": self.canonical_url,
                "selected_source_methods": self.selected_source_methods,
                "result_status": self.result_status.value,
            }
        )
        return data


@dataclass(frozen=True)
class OperationalCaptureRuntimeBundle:
    bundle_id: str
    fixtures: tuple[OperationalFixtureDescriptor, ...]
    runtime_results: tuple[OperationalCaptureRuntimeResult, ...]
    no_live_execution: bool = True
    approval_required: bool = True
    completed_evidence_claimed: bool = False
    schema_version: str = SOURCE_OPERATIONAL_CAPTURE_RUNTIME_SCHEMA_VERSION

    @property
    def fixture_count(self) -> int:
        return len(self.fixtures)

    @property
    def runtime_result_count(self) -> int:
        return len(self.runtime_results)

    @property
    def warning_count(self) -> int:
        return sum(len(result.warning_flags) for result in self.runtime_results)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["fixture_count"] = self.fixture_count
        data["runtime_result_count"] = self.runtime_result_count
        data["warning_count"] = self.warning_count
        return data


def validate_operational_runtime_result(data: Mapping[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    status = str(data.get("result_status", ""))
    if status not in {item.value for item in OperationalResultStatus}:
        errors.append(f"unsupported_status:{status}")
    if status in UNSAFE_COMPLETION_STATUSES:
        errors.append("completed_or_live_status_not_allowed_without_verified_approval")
    for key in (
        "completed_evidence_claimed",
        "verified_evidence_claimed",
        "live_network_performed",
        "browser_automation_performed",
        "archive_provider_call_performed",
        "download_performed",
        "file_move_performed",
        "raw_payload_included",
    ):
        if bool(data.get(key, False)):
            errors.append(f"unsafe_flag_true:{key}")
    if not bool(data.get("no_live_execution", False)):
        errors.append("no_live_execution_must_be_true")
    return tuple(errors)


def build_default_operational_fixture_matrix() -> tuple[OperationalFixtureDescriptor, ...]:
    fixture_rows = (
        ("fixture_static_article", "article", "Static article HTML", ("article_text", "visible_outline"), ()),
        ("fixture_js_state_article", "article", "JavaScript-like article state data", ("article_text",), ()),
        ("fixture_page_chrome", "article", "Page chrome separated from article text", ("visible_outline",), ()),
        ("fixture_low_confidence_article", "article", "Low-confidence article fallback", ("reviewable_fallback",), ("low_confidence",)),
        ("fixture_comments_normal", "comments", "Ordinary DOM comments", ("comments_json",), ()),
        ("fixture_comments_load_more", "comments", "Load-more comments", ("comments_json",), ("partial_until_load_more_complete",)),
        ("fixture_comments_iframe", "comments", "Iframe comments", ("comments_json",), ()),
        ("fixture_comments_open_shadow", "comments", "Open shadow-root comments", ("comments_json",), ()),
        ("fixture_comments_closed_shadow_plan", "comments", "Closed-shadow planned hook", ("operator_hook_plan",), ("approval_required",)),
        ("fixture_comments_nested_scroll", "comments", "Nested scroll comments", ("comments_json",), ()),
        ("fixture_comments_virtualized", "comments", "Virtualized/recycled comments", ("incremental_comments_checkpoint",), ()),
        ("fixture_comments_deleted", "comments", "Disappearing/deleted comments", ("comment_tombstone",), ()),
        ("fixture_encoded_state", "decoded_state", "Encoded/page-decoded state", ("decoded_state_metadata",), ()),
        ("fixture_login_required", "challenge", "Login-required state", ("manual_fallback_receipt",), ("challenge_detected",)),
        ("fixture_challenge_required", "challenge", "Challenge-required state", ("pause_resume_receipt",), ("challenge_detected",)),
        ("fixture_livechat_stream", "livechat", "Bounded livechat message stream", ("livechat_json",), ()),
        ("fixture_image_srcset_css", "media", "Images, srcset and CSS backgrounds", ("media_inventory",), ()),
        ("fixture_playback_media", "media", "Playback-gated media metadata", ("media_inventory",), ("playback_trigger_required",)),
        ("fixture_signed_url", "media", "Signed URL metadata", ("media_inventory",), ("expires_without_refresh",)),
        ("fixture_blob_media_source", "media", "Blob/MediaSource metadata", ("non_downloadable_resource",), ("non_downloadable",)),
        ("fixture_hls_manifest", "media", "HLS manifest", ("hls_manifest_plan",), ()),
        ("fixture_dash_manifest", "media", "DASH manifest", ("dash_manifest_plan",), ()),
        ("fixture_separate_tracks", "media", "Separate audio/video/subtitle tracks", ("mux_command_plan",), ()),
        ("fixture_protected_output", "rendered_citation", "DRM/protected-output mock", ("blocked_rendered_capture",), ("protected_output_blocked",)),
        ("fixture_wayback_responses", "archive", "Wayback mocked responses", ("archive_provider_result",), ()),
        ("fixture_archive_today_responses", "archive", "archive.today mocked responses", ("archive_provider_result",), ()),
        ("fixture_archivebox_command", "archivebox", "ArchiveBox command mock", ("archivebox_command_plan",), ()),
    )
    return tuple(
        OperationalFixtureDescriptor(
            fixture_id=fixture_id,
            category=category,
            label=label,
            artifact_expectations=tuple(artifact_expectations),
            warning_flags=tuple(warning_flags),
        )
        for fixture_id, category, label, artifact_expectations, warning_flags in fixture_rows
    )


def build_fixture_operational_capture_runtime_bundle(
    *,
    source_url: str = "https://example.invalid/source",
    canonical_url: str = "https://example.invalid/source",
    created_at_utc: str = "2026-08-08T00:00:00Z",
    selected_source_methods: tuple[str, ...] = (
        "generic_article_html",
        "generic_comments_manual_import",
        "archive_only_import",
    ),
) -> OperationalCaptureRuntimeBundle:
    fixtures = build_default_operational_fixture_matrix()
    result = OperationalCaptureRuntimeResult(
        capture_session_id="fixture_capture_session_" + _sha16((source_url, selected_source_methods)),
        source_url=source_url,
        canonical_url=canonical_url,
        access_mode="localhost_fixture_or_mock_only",
        capture_method="fixture_operational_capture",
        selected_source_methods=_stable_tuple(selected_source_methods),
        operator_approval_state="approval_required_for_live_execution",
        started_at_utc=created_at_utc,
        finished_at_utc=created_at_utc,
        result_status=OperationalResultStatus.FIXTURE_TESTED,
        artifact_references=tuple(
            f"fixture_artifact:{fixture.fixture_id}:{artifact}"
            for fixture in fixtures
            for artifact in fixture.artifact_expectations
        ),
        receipt_references=("receipt:not_live_executed", "receipt:fixture_tested"),
        warning_flags=_stable_tuple(flag for fixture in fixtures for flag in fixture.warning_flags),
        completeness_flags=(
            "fixture_matrix_complete_for_non_live_operational_layer",
            "live_site_manual_verification_pending",
        ),
        hash_chained_log_reference="source_behavior_provenance_log.json",
    )
    return OperationalCaptureRuntimeBundle(
        bundle_id="operational_runtime_bundle_" + _sha16(result.to_dict()),
        fixtures=fixtures,
        runtime_results=(result,),
    )


def source_operational_capture_runtime_bundle_to_json(
    bundle: OperationalCaptureRuntimeBundle,
) -> str:
    return _stable_json(bundle.to_dict(), pretty=True)
