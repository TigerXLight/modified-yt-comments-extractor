from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Sequence

from capture_twitter_exporter_action_receipt import (
    TwitterExporterActionReceipt,
    build_twitter_exporter_action_receipt_summary,
    build_twitter_exporter_import_action_receipt,
)
from capture_twitter_exporter_manifest_report import (
    TwitterExporterManifestReport,
    build_twitter_exporter_manifest_report,
    build_twitter_exporter_manifest_report_text,
)
from capture_twitter_exporter_source_import import (
    TwitterExporterQueueReviewDraft,
    TwitterExporterSourceImportReviewState,
    build_twitter_exporter_queue_review_draft,
    build_twitter_exporter_queue_review_draft_summary,
    build_twitter_exporter_source_row_summary,
    preview_twitter_exporter_local_import_source,
)


TWITTER_EXPORTER_REVIEW_FLOW_SCHEMA_VERSION = "twitter_exporter_review_flow.v1"
TWITTER_EXPORTER_REVIEW_FLOW_SCOPE = (
    "Twitter/X exporter end-to-end local review flow metadata only; explicit local "
    "user-supplied exporter files only; summary/counts only; no raw tweet text, "
    "record payloads, full local paths, live verification, API capture, browser "
    "automation, extension automation, archive, download, screenshot/OCR, WARC/WACZ, "
    "completed-evidence, evidence-file move, or automatic classification claims"
)


def _stable_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _stable_id(prefix: str, data: dict[str, Any]) -> str:
    digest = hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


@dataclass(frozen=True)
class TwitterExporterReviewFlowFileSummary:
    input_index: int
    input_file_name: str
    status: str
    input_file_sha256: str = ""
    input_file_size_bytes: int = 0
    archive_member_count: int = 0
    parsed_record_count: int = 0
    skipped_record_count: int = 0
    warning_count: int = 0
    validation_error_count: int = 0
    import_bundle_id: str = ""
    queue_draft_item_id: str = ""
    manifest_entry_id: str = ""
    receipt_queue_draft_item_id: str = ""
    warnings: tuple[str, ...] = ()
    validation_errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["validation_errors"] = list(self.validation_errors)
        data["warnings"] = list(self.warnings)
        return data


@dataclass(frozen=True)
class TwitterExporterLocalReviewFlow:
    flow_id: str
    source_review_state: TwitterExporterSourceImportReviewState
    queue_draft: TwitterExporterQueueReviewDraft
    manifest_report: TwitterExporterManifestReport
    action_receipt: TwitterExporterActionReceipt
    file_summaries: tuple[TwitterExporterReviewFlowFileSummary, ...]
    status: str
    review_status: str = "USER_REVIEW_REQUIRED"
    provenance_status: str = "USER_SUPPLIED_LOCAL_EXPORT"
    summary_only: bool = True
    user_review_required: bool = True
    local_path_included: bool = False
    raw_record_payload_included: bool = False
    tweet_text_included: bool = False
    live_verification_claimed: bool = False
    api_capture_claimed: bool = False
    browser_automation_claimed: bool = False
    extension_automation_claimed: bool = False
    archive_claimed: bool = False
    archive_provider_result_claimed: bool = False
    downloaded_media_claimed: bool = False
    screenshot_ocr_claimed: bool = False
    screenshot_claimed: bool = False
    ocr_claimed: bool = False
    warc_wacz_claimed: bool = False
    completed_evidence_claimed: bool = False
    evidence_file_move_claimed: bool = False
    automatic_classification_claimed: bool = False
    automatic_classification: bool = False
    network_actions_performed: str = "none"
    schema_version: str = TWITTER_EXPORTER_REVIEW_FLOW_SCHEMA_VERSION
    scope: str = TWITTER_EXPORTER_REVIEW_FLOW_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_receipt_summary": {
                "action_log_event_hash": self.action_receipt.action_log_event.to_dict()["event_hash"],
                "action_log_event_id": self.action_receipt.action_log_event.event_id,
                "action_type": self.action_receipt.action_type,
                "manifest_report_entry_count": self.action_receipt.manifest_report_entry_count,
                "queue_draft_count": self.action_receipt.queue_draft_count,
                "receipt_id": self.action_receipt.receipt_id,
                "result": self.action_receipt.result,
                "summary_only": self.action_receipt.summary_only,
            },
            "api_capture_claimed": self.api_capture_claimed,
            "archive_claimed": self.archive_claimed,
            "archive_provider_result_claimed": self.archive_provider_result_claimed,
            "automatic_classification": self.automatic_classification,
            "automatic_classification_claimed": self.automatic_classification_claimed,
            "browser_automation_claimed": self.browser_automation_claimed,
            "completed_evidence_claimed": self.completed_evidence_claimed,
            "downloaded_media_claimed": self.downloaded_media_claimed,
            "evidence_file_move_claimed": self.evidence_file_move_claimed,
            "extension_automation_claimed": self.extension_automation_claimed,
            "file_summaries": [summary.to_dict() for summary in self.file_summaries],
            "flow_id": self.flow_id,
            "input_count": self.source_review_state.input_count,
            "live_verification_claimed": self.live_verification_claimed,
            "local_path_included": self.local_path_included,
            "manifest_report_summary": {
                "entry_count": len(self.manifest_report.entries),
                "no_entries_reason": self.manifest_report.no_entries_reason,
                "report_id": self.manifest_report.report_id,
                "summary_only": self.manifest_report.summary_only,
                "total_error_count": self.manifest_report.total_error_count,
                "total_parsed_record_count": self.manifest_report.total_parsed_record_count,
                "total_skipped_record_count": self.manifest_report.total_skipped_record_count,
                "total_warning_count": self.manifest_report.total_warning_count,
            },
            "network_actions_performed": self.network_actions_performed,
            "ocr_claimed": self.ocr_claimed,
            "provenance_status": self.provenance_status,
            "queue_draft_summary": {
                "draft_id": self.queue_draft.draft_id,
                "draft_status": self.queue_draft.draft_status,
                "eligible_input_count": self.queue_draft.eligible_input_count,
                "queue_metadata_only": self.queue_draft.queue_metadata_only,
                "rejected_input_count": self.queue_draft.rejected_input_count,
                "total_error_count": self.queue_draft.total_error_count,
                "total_parsed_record_count": self.queue_draft.total_parsed_record_count,
                "total_skipped_record_count": self.queue_draft.total_skipped_record_count,
                "total_warning_count": self.queue_draft.total_warning_count,
            },
            "raw_record_payload_included": self.raw_record_payload_included,
            "review_status": self.review_status,
            "schema_version": self.schema_version,
            "screenshot_claimed": self.screenshot_claimed,
            "screenshot_ocr_claimed": self.screenshot_ocr_claimed,
            "scope": self.scope,
            "source_review_summary": {
                "input_count": self.source_review_state.input_count,
                "queue_metadata_available": self.source_review_state.queue_metadata_available,
                "source_kind": self.source_review_state.source_kind,
                "source_platform": self.source_review_state.source_platform,
                "summary_only_preview": self.source_review_state.summary_only_preview,
                "total_error_count": self.source_review_state.total_error_count,
                "total_parsed_record_count": self.source_review_state.total_parsed_record_count,
                "total_skipped_record_count": self.source_review_state.total_skipped_record_count,
                "total_warning_count": self.source_review_state.total_warning_count,
            },
            "status": self.status,
            "summary_only": self.summary_only,
            "tweet_text_included": self.tweet_text_included,
            "user_review_required": self.user_review_required,
            "warc_wacz_claimed": self.warc_wacz_claimed,
        }


def _manifest_entry_ids_by_queue_item_id(
    report: TwitterExporterManifestReport,
) -> dict[str, str]:
    return {entry.queue_draft_item_id: entry.entry_id for entry in report.entries}


def _queue_item_ids_by_import_bundle_id(
    draft: TwitterExporterQueueReviewDraft,
) -> dict[str, str]:
    return {
        str(item.get("import_bundle_id", "")): str(item.get("item_id", ""))
        for item in draft.queue_review_items
        if item.get("import_bundle_id")
    }


def _receipt_queue_item_ids_by_import_bundle_id(
    receipt: TwitterExporterActionReceipt,
) -> dict[str, str]:
    return {
        entry.import_bundle_id: entry.queue_draft_item_id
        for entry in receipt.file_entries
        if entry.import_bundle_id
    }


def _flow_file_summaries(
    *,
    state: TwitterExporterSourceImportReviewState,
    draft: TwitterExporterQueueReviewDraft,
    report: TwitterExporterManifestReport,
    receipt: TwitterExporterActionReceipt,
) -> tuple[TwitterExporterReviewFlowFileSummary, ...]:
    queue_ids = _queue_item_ids_by_import_bundle_id(draft)
    manifest_ids = _manifest_entry_ids_by_queue_item_id(report)
    receipt_queue_ids = _receipt_queue_item_ids_by_import_bundle_id(receipt)
    summaries: list[TwitterExporterReviewFlowFileSummary] = []
    for summary in sorted(state.file_summaries, key=lambda item: item.input_index):
        queue_item_id = queue_ids.get(summary.import_bundle_id, "")
        summaries.append(
            TwitterExporterReviewFlowFileSummary(
                input_index=summary.input_index,
                input_file_name=summary.input_file_name,
                status=summary.status,
                input_file_sha256=summary.input_file_sha256,
                input_file_size_bytes=summary.input_file_size_bytes,
                archive_member_count=summary.archive_member_count,
                parsed_record_count=summary.parsed_record_count,
                skipped_record_count=summary.skipped_record_count,
                warning_count=summary.warning_count,
                validation_error_count=summary.validation_error_count,
                import_bundle_id=summary.import_bundle_id,
                queue_draft_item_id=queue_item_id,
                manifest_entry_id=manifest_ids.get(queue_item_id, ""),
                receipt_queue_draft_item_id=receipt_queue_ids.get(summary.import_bundle_id, ""),
                warnings=summary.warnings,
                validation_errors=summary.validation_errors,
            )
        )
    return tuple(summaries)


def build_twitter_exporter_local_review_flow(
    input_paths: Sequence[str],
    *,
    session_id: str,
    timestamp_utc: str,
    previous_event_hash: str = "",
    actor_id: str = "",
    app_version: str = "",
    max_zip_entries: int = 5000,
    max_total_uncompressed_bytes: int = 250 * 1024 * 1024,
    max_single_file_bytes: int = 50 * 1024 * 1024,
) -> TwitterExporterLocalReviewFlow:
    state = preview_twitter_exporter_local_import_source(
        input_paths,
        max_zip_entries=max_zip_entries,
        max_total_uncompressed_bytes=max_total_uncompressed_bytes,
        max_single_file_bytes=max_single_file_bytes,
    )
    draft = build_twitter_exporter_queue_review_draft(state)
    report = build_twitter_exporter_manifest_report(draft)
    receipt = build_twitter_exporter_import_action_receipt(
        state,
        session_id=session_id,
        timestamp_utc=timestamp_utc,
        previous_event_hash=previous_event_hash,
        actor_id=actor_id,
        app_version=app_version,
    )
    file_summaries = _flow_file_summaries(
        state=state,
        draft=draft,
        report=report,
        receipt=receipt,
    )
    status = "USER_REVIEW_REQUIRED" if draft.queue_review_items else "REVIEW_ERROR"
    flow_id = _stable_id(
        "twitter_exporter_review_flow",
        {
            "action_receipt_id": receipt.receipt_id,
            "draft_id": draft.draft_id,
            "file_names": tuple(summary.input_file_name for summary in file_summaries),
            "manifest_report_id": report.report_id,
            "schema_version": TWITTER_EXPORTER_REVIEW_FLOW_SCHEMA_VERSION,
            "session_id": session_id,
            "timestamp_utc": timestamp_utc,
        },
    )
    return TwitterExporterLocalReviewFlow(
        flow_id=flow_id,
        source_review_state=state,
        queue_draft=draft,
        manifest_report=report,
        action_receipt=receipt,
        file_summaries=file_summaries,
        status=status,
    )


def run_twitter_exporter_local_review_flow(
    input_paths: Sequence[str],
    **kwargs: Any,
) -> TwitterExporterLocalReviewFlow:
    return build_twitter_exporter_local_review_flow(input_paths, **kwargs)


def twitter_exporter_review_flow_to_json(flow: TwitterExporterLocalReviewFlow) -> str:
    return json.dumps(flow.to_dict(), indent=2, sort_keys=True)


def build_twitter_exporter_review_flow_summary(flow: TwitterExporterLocalReviewFlow) -> str:
    source_summary = build_twitter_exporter_source_row_summary(flow.source_review_state)
    queue_summary = build_twitter_exporter_queue_review_draft_summary(flow.queue_draft)
    manifest_summary = build_twitter_exporter_manifest_report_text(flow.queue_draft)
    receipt_summary = build_twitter_exporter_action_receipt_summary(flow.action_receipt)
    lines = [
        "Twitter/X exporter end-to-end local review flow",
        f"Flow ID: {flow.flow_id}",
        f"Status: {flow.status}",
        f"Review status: {flow.review_status}",
        f"Provenance: {flow.provenance_status}",
        f"Inputs: {flow.source_review_state.input_count}",
        f"Queue draft items: {flow.queue_draft.eligible_input_count}",
        f"Manifest/report entries: {len(flow.manifest_report.entries)}",
        f"Action receipt result: {flow.action_receipt.result}",
        "Summary/counts only: yes",
        "Network actions performed: none",
        "Live/API/browser/extension/archive/download/OCR/WARC/WACZ/classification/completed-evidence claims: none",
        "",
        source_summary,
        "",
        queue_summary,
        "",
        manifest_summary,
        "",
        receipt_summary,
    ]
    return "\n".join(lines)


__all__ = [
    "TWITTER_EXPORTER_REVIEW_FLOW_SCHEMA_VERSION",
    "TWITTER_EXPORTER_REVIEW_FLOW_SCOPE",
    "TwitterExporterLocalReviewFlow",
    "TwitterExporterReviewFlowFileSummary",
    "build_twitter_exporter_local_review_flow",
    "build_twitter_exporter_review_flow_summary",
    "run_twitter_exporter_local_review_flow",
    "twitter_exporter_review_flow_to_json",
]
