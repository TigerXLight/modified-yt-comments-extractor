from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from capture_action_log import ACTOR_TYPE_APPLICATION, CaptureActionLogEvent, build_action_log_event
from capture_twitter_exporter_manifest_report import (
    TwitterExporterManifestReport,
    build_twitter_exporter_manifest_report,
)
from capture_twitter_exporter_source_import import (
    TwitterExporterQueueReviewDraft,
    TwitterExporterSourceImportFileSummary,
    TwitterExporterSourceImportReviewState,
    build_twitter_exporter_queue_review_draft,
)


TWITTER_EXPORTER_ACTION_RECEIPT_SCHEMA_VERSION = "twitter_exporter_action_receipt.v1"
TWITTER_EXPORTER_ACTION_TYPE = "twitter_x_local_export_import_review"
TWITTER_EXPORTER_ACTION_RECEIPT_SCOPE = (
    "Twitter/X exporter local import action-log/provenance receipt metadata only; "
    "summary/counts only; no raw tweet text, record payloads, full local paths, live "
    "verification, API capture, browser automation, extension automation, archive, "
    "download, screenshot/OCR, WARC/WACZ, completed-evidence, evidence-file move, "
    "or automatic classification claims"
)


def _stable_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _stable_id(prefix: str, data: dict[str, Any]) -> str:
    digest = hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


@dataclass(frozen=True)
class TwitterExporterActionReceiptFileEntry:
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
    import_status: str = ""
    queue_draft_item_id: str = ""
    warnings: tuple[str, ...] = ()
    validation_errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["validation_errors"] = list(self.validation_errors)
        data["warnings"] = list(self.warnings)
        return data


@dataclass(frozen=True)
class TwitterExporterActionReceipt:
    receipt_id: str
    action_type: str
    result: str
    timestamp_utc: str
    session_id: str
    file_entries: tuple[TwitterExporterActionReceiptFileEntry, ...]
    action_log_event: CaptureActionLogEvent
    input_count: int
    eligible_input_count: int
    rejected_input_count: int
    queue_draft_count: int
    manifest_report_entry_count: int
    total_parsed_record_count: int
    total_skipped_record_count: int
    total_warning_count: int
    total_error_count: int
    importer_name: str = "Twitter Exporter"
    importer_source: str = "twitter_exporter_user_supplied_local_file"
    source_platform: str = "twitter_x"
    source_kind: str = "local_export"
    review_status: str = "USER_REVIEW_REQUIRED"
    provenance_status: str = "USER_SUPPLIED_LOCAL_EXPORT"
    user_review_required: bool = True
    summary_only: bool = True
    provenance_receipt_only: bool = True
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
    schema_version: str = TWITTER_EXPORTER_ACTION_RECEIPT_SCHEMA_VERSION
    scope: str = TWITTER_EXPORTER_ACTION_RECEIPT_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_log_event": self.action_log_event.to_dict(),
            "action_type": self.action_type,
            "api_capture_claimed": self.api_capture_claimed,
            "archive_claimed": self.archive_claimed,
            "archive_provider_result_claimed": self.archive_provider_result_claimed,
            "automatic_classification": self.automatic_classification,
            "automatic_classification_claimed": self.automatic_classification_claimed,
            "browser_automation_claimed": self.browser_automation_claimed,
            "completed_evidence_claimed": self.completed_evidence_claimed,
            "downloaded_media_claimed": self.downloaded_media_claimed,
            "eligible_input_count": self.eligible_input_count,
            "evidence_file_move_claimed": self.evidence_file_move_claimed,
            "extension_automation_claimed": self.extension_automation_claimed,
            "file_entries": [entry.to_dict() for entry in self.file_entries],
            "importer_name": self.importer_name,
            "importer_source": self.importer_source,
            "input_count": self.input_count,
            "live_verification_claimed": self.live_verification_claimed,
            "local_path_included": self.local_path_included,
            "manifest_report_entry_count": self.manifest_report_entry_count,
            "network_actions_performed": self.network_actions_performed,
            "ocr_claimed": self.ocr_claimed,
            "provenance_receipt_only": self.provenance_receipt_only,
            "provenance_status": self.provenance_status,
            "queue_draft_count": self.queue_draft_count,
            "raw_record_payload_included": self.raw_record_payload_included,
            "receipt_id": self.receipt_id,
            "rejected_input_count": self.rejected_input_count,
            "result": self.result,
            "review_status": self.review_status,
            "schema_version": self.schema_version,
            "scope": self.scope,
            "screenshot_claimed": self.screenshot_claimed,
            "screenshot_ocr_claimed": self.screenshot_ocr_claimed,
            "session_id": self.session_id,
            "source_kind": self.source_kind,
            "source_platform": self.source_platform,
            "summary_only": self.summary_only,
            "timestamp_utc": self.timestamp_utc,
            "total_error_count": self.total_error_count,
            "total_parsed_record_count": self.total_parsed_record_count,
            "total_skipped_record_count": self.total_skipped_record_count,
            "total_warning_count": self.total_warning_count,
            "tweet_text_included": self.tweet_text_included,
            "user_review_required": self.user_review_required,
            "warc_wacz_claimed": self.warc_wacz_claimed,
        }


def _queue_item_ids_by_import_bundle_id(
    draft: TwitterExporterQueueReviewDraft,
) -> dict[str, str]:
    return {
        str(item.get("import_bundle_id", "")): str(item.get("item_id", ""))
        for item in draft.queue_review_items
        if item.get("import_bundle_id")
    }


def _receipt_entry_from_summary(
    summary: TwitterExporterSourceImportFileSummary,
    *,
    queue_item_ids: dict[str, str],
) -> TwitterExporterActionReceiptFileEntry:
    return TwitterExporterActionReceiptFileEntry(
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
        import_status=summary.import_status,
        queue_draft_item_id=queue_item_ids.get(summary.import_bundle_id, ""),
        warnings=summary.warnings,
        validation_errors=summary.validation_errors,
    )


def _request_summary(
    *,
    state: TwitterExporterSourceImportReviewState,
    draft: TwitterExporterQueueReviewDraft,
    manifest_report: TwitterExporterManifestReport,
    file_entries: tuple[TwitterExporterActionReceiptFileEntry, ...],
    receipt_id: str,
) -> dict[str, Any]:
    return {
        "action_type": TWITTER_EXPORTER_ACTION_TYPE,
        "api_capture_claimed": False,
        "archive_claimed": False,
        "archive_provider_result_claimed": False,
        "automatic_classification": False,
        "browser_automation_claimed": False,
        "completed_evidence_claimed": False,
        "downloaded_media_claimed": False,
        "evidence_file_move_claimed": False,
        "extension_automation_claimed": False,
        "file_entries": [entry.to_dict() for entry in file_entries],
        "importer_name": state.importer_name,
        "importer_source": state.importer_source,
        "input_count": state.input_count,
        "live_verification_claimed": False,
        "local_path_included": False,
        "manifest_report_entry_count": len(manifest_report.entries),
        "network_actions_performed": "none",
        "ocr_claimed": False,
        "provenance_status": state.provenance_status,
        "queue_draft_count": len(draft.queue_review_items),
        "raw_record_payload_included": False,
        "receipt_id": receipt_id,
        "review_status": state.review_status,
        "screenshot_claimed": False,
        "screenshot_ocr_claimed": False,
        "source_kind": state.source_kind,
        "source_platform": state.source_platform,
        "summary_only": True,
        "total_error_count": state.total_error_count,
        "total_parsed_record_count": state.total_parsed_record_count,
        "total_skipped_record_count": state.total_skipped_record_count,
        "total_warning_count": state.total_warning_count,
        "tweet_text_included": False,
        "user_review_required": True,
        "warc_wacz_claimed": False,
    }


def build_twitter_exporter_import_action_receipt(
    state: TwitterExporterSourceImportReviewState,
    *,
    session_id: str,
    timestamp_utc: str,
    previous_event_hash: str = "",
    actor_id: str = "",
    app_version: str = "",
) -> TwitterExporterActionReceipt:
    if not session_id:
        raise ValueError("Twitter exporter action receipt requires session_id.")
    if not timestamp_utc:
        raise ValueError("Twitter exporter action receipt requires explicit timestamp_utc.")
    draft = build_twitter_exporter_queue_review_draft(state)
    manifest_report = build_twitter_exporter_manifest_report(draft)
    queue_item_ids = _queue_item_ids_by_import_bundle_id(draft)
    file_entries = tuple(
        _receipt_entry_from_summary(summary, queue_item_ids=queue_item_ids)
        for summary in sorted(state.file_summaries, key=lambda item: item.input_index)
    )
    result = "USER_REVIEW_REQUIRED" if draft.queue_review_items else "REVIEW_ERROR"
    receipt_id = _stable_id(
        "twitter_exporter_action_receipt",
        {
            "draft_id": draft.draft_id,
            "file_entry_names": tuple(entry.input_file_name for entry in file_entries),
            "manifest_report_id": manifest_report.report_id,
            "schema_version": TWITTER_EXPORTER_ACTION_RECEIPT_SCHEMA_VERSION,
            "session_id": session_id,
            "timestamp_utc": timestamp_utc,
        },
    )
    summary = _request_summary(
        state=state,
        draft=draft,
        manifest_report=manifest_report,
        file_entries=file_entries,
        receipt_id=receipt_id,
    )
    event = build_action_log_event(
        session_id=session_id,
        actor_type=ACTOR_TYPE_APPLICATION,
        actor_id=actor_id,
        action_type=TWITTER_EXPORTER_ACTION_TYPE,
        result=result,
        timestamp_utc=timestamp_utc,
        previous_event_hash=previous_event_hash,
        request_summary=summary,
        artifact_ids=(draft.draft_id, manifest_report.report_id),
        app_version=app_version,
    )
    return TwitterExporterActionReceipt(
        receipt_id=receipt_id,
        action_type=TWITTER_EXPORTER_ACTION_TYPE,
        result=result,
        timestamp_utc=timestamp_utc,
        session_id=session_id,
        file_entries=file_entries,
        action_log_event=event,
        input_count=state.input_count,
        eligible_input_count=draft.eligible_input_count,
        rejected_input_count=draft.rejected_input_count,
        queue_draft_count=len(draft.queue_review_items),
        manifest_report_entry_count=len(manifest_report.entries),
        total_parsed_record_count=state.total_parsed_record_count,
        total_skipped_record_count=state.total_skipped_record_count,
        total_warning_count=state.total_warning_count,
        total_error_count=state.total_error_count,
    )


def twitter_exporter_action_receipt_to_json(receipt: TwitterExporterActionReceipt) -> str:
    return json.dumps(receipt.to_dict(), indent=2, sort_keys=True)


def build_twitter_exporter_action_receipt_summary(
    receipt: TwitterExporterActionReceipt,
) -> str:
    lines = [
        "Twitter/X exporter local import provenance receipt",
        f"Receipt ID: {receipt.receipt_id}",
        f"Result: {receipt.result}",
        f"Review status: {receipt.review_status}",
        f"Provenance: {receipt.provenance_status}",
        f"Inputs: {receipt.input_count}",
        f"Queue draft items: {receipt.queue_draft_count}",
        f"Manifest/report entries: {receipt.manifest_report_entry_count}",
        f"Rejected inputs: {receipt.rejected_input_count}",
        f"Parsed records: {receipt.total_parsed_record_count}",
        f"Skipped records: {receipt.total_skipped_record_count}",
        f"Warnings: {receipt.total_warning_count}",
        f"Errors: {receipt.total_error_count}",
        "Summary/counts only: yes",
        "Network actions performed: none",
        "Live/API/browser/extension/archive/download/OCR/WARC/WACZ/classification/completed-evidence claims: none",
        "Files:",
    ]
    if not receipt.file_entries:
        lines.append("- (none)")
    for entry in receipt.file_entries:
        lines.append(
            "- "
            f"{entry.input_file_name}: "
            f"{entry.status}, "
            f"{entry.parsed_record_count} parsed, "
            f"{entry.skipped_record_count} skipped, "
            f"{entry.warning_count} warning(s), "
            f"{entry.validation_error_count} error(s), "
            f"{entry.archive_member_count} archive member(s), "
            f"sha256 {entry.input_file_sha256}"
        )
    return "\n".join(lines)


__all__ = [
    "TWITTER_EXPORTER_ACTION_RECEIPT_SCHEMA_VERSION",
    "TWITTER_EXPORTER_ACTION_RECEIPT_SCOPE",
    "TWITTER_EXPORTER_ACTION_TYPE",
    "TwitterExporterActionReceipt",
    "TwitterExporterActionReceiptFileEntry",
    "build_twitter_exporter_action_receipt_summary",
    "build_twitter_exporter_import_action_receipt",
    "twitter_exporter_action_receipt_to_json",
]
