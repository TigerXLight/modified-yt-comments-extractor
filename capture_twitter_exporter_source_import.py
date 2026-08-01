from __future__ import annotations

import json
import hashlib
from dataclasses import asdict, dataclass
from typing import Any, Sequence

from evidence_item_queue import EvidenceItemRole, EvidenceItemStatus, EvidenceQueueItem

from capture_twitter_exporter_import import (
    TWITTER_EXPORTER_IMPORTER_NAME,
    TWITTER_EXPORTER_IMPORTER_SOURCE,
    TWITTER_EXPORTER_PROVENANCE_USER_SUPPLIED_LOCAL_EXPORT,
    TWITTER_EXPORTER_REVIEW_STATUS_USER_REVIEW_REQUIRED,
    TWITTER_EXPORTER_SOURCE_KIND,
    TWITTER_EXPORTER_SOURCE_PLATFORM,
)
from capture_twitter_exporter_import_cli import build_twitter_exporter_import_cli_result


TWITTER_EXPORTER_SOURCE_ROW_KIND = "twitter_exporter_local_import"
TWITTER_EXPORTER_QUEUE_DRAFT_SCHEMA_VERSION = "twitter_exporter_source_queue_draft.v1"
TWITTER_EXPORTER_SOURCE_IMPORT_SCOPE = (
    "Twitter/X exporter source-workflow local import preview only; explicit local files "
    "only; no X/Twitter API, browser capture, browser automation, extension automation, "
    "network, archive, download, screenshot/OCR, credential, broad folder scan, "
    "evidence file move, or automatic classification behavior"
)
TWITTER_EXPORTER_QUEUE_HANDOFF_SCOPE = (
    "Twitter/X exporter source review to export/evidence queue draft metadata only; "
    "explicit local user-supplied exporter files only; summary/counts only; no raw "
    "tweet text, X/Twitter API, browser capture, browser automation, extension "
    "automation, network, archive, download, screenshot/OCR, credential, evidence "
    "file move, completed-evidence claim, or automatic classification behavior"
)


def _stable_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _stable_id(prefix: str, data: dict[str, Any]) -> str:
    digest = hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


@dataclass(frozen=True)
class TwitterExporterSourceImportFileSummary:
    input_index: int
    input_file_name: str
    status: str
    import_bundle_id: str = ""
    import_status: str = ""
    input_file_sha256: str = ""
    input_file_size_bytes: int = 0
    archive_member_count: int = 0
    parsed_record_count: int = 0
    skipped_record_count: int = 0
    warning_count: int = 0
    validation_error_count: int = 0
    warnings: tuple[str, ...] = ()
    validation_errors: tuple[str, ...] = ()
    source_platform: str = TWITTER_EXPORTER_SOURCE_PLATFORM
    source_kind: str = TWITTER_EXPORTER_SOURCE_KIND
    importer_name: str = TWITTER_EXPORTER_IMPORTER_NAME
    importer_source: str = TWITTER_EXPORTER_IMPORTER_SOURCE
    source_row_kind: str = TWITTER_EXPORTER_SOURCE_ROW_KIND
    review_status: str = TWITTER_EXPORTER_REVIEW_STATUS_USER_REVIEW_REQUIRED
    provenance_status: str = TWITTER_EXPORTER_PROVENANCE_USER_SUPPLIED_LOCAL_EXPORT
    queue_metadata_available: bool = False
    summary_only_preview: bool = True
    live_verification_claimed: bool = False
    api_capture_claimed: bool = False
    browser_capture_claimed: bool = False
    browser_automation_claimed: bool = False
    extension_automation_claimed: bool = False
    archive_claimed: bool = False
    archive_provider_result_claimed: bool = False
    screenshot_ocr_claimed: bool = False
    screenshot_claimed: bool = False
    ocr_claimed: bool = False
    media_download_claimed: bool = False
    downloaded_media_claimed: bool = False
    automatic_classification_claimed: bool = False
    automatic_classification: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["warnings"] = list(self.warnings)
        data["validation_errors"] = list(self.validation_errors)
        return data


@dataclass(frozen=True)
class TwitterExporterSourceImportReviewState:
    file_summaries: tuple[TwitterExporterSourceImportFileSummary, ...]
    input_count: int
    total_parsed_record_count: int
    total_skipped_record_count: int
    total_warning_count: int
    total_error_count: int
    queue_review_items: tuple[dict[str, Any], ...] = ()
    queue_items: tuple[dict[str, Any], ...] = ()
    source_platform: str = TWITTER_EXPORTER_SOURCE_PLATFORM
    source_kind: str = TWITTER_EXPORTER_SOURCE_KIND
    importer_name: str = TWITTER_EXPORTER_IMPORTER_NAME
    importer_source: str = TWITTER_EXPORTER_IMPORTER_SOURCE
    source_row_kind: str = TWITTER_EXPORTER_SOURCE_ROW_KIND
    review_status: str = TWITTER_EXPORTER_REVIEW_STATUS_USER_REVIEW_REQUIRED
    provenance_status: str = TWITTER_EXPORTER_PROVENANCE_USER_SUPPLIED_LOCAL_EXPORT
    user_review_required: bool = True
    input_order: str = "input_order_preserved"
    summary_only_preview: bool = True
    queue_metadata_requested: bool = False
    queue_metadata_available: bool = False
    live_verification_claimed: bool = False
    api_capture_claimed: bool = False
    browser_capture_claimed: bool = False
    browser_automation_claimed: bool = False
    extension_automation_claimed: bool = False
    archive_claimed: bool = False
    archive_provider_result_claimed: bool = False
    screenshot_ocr_claimed: bool = False
    screenshot_claimed: bool = False
    ocr_claimed: bool = False
    media_download_claimed: bool = False
    downloaded_media_claimed: bool = False
    automatic_classification_claimed: bool = False
    automatic_classification: bool = False
    network_actions_performed: str = "none"
    scope: str = TWITTER_EXPORTER_SOURCE_IMPORT_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "api_capture_claimed": self.api_capture_claimed,
            "archive_claimed": self.archive_claimed,
            "archive_provider_result_claimed": self.archive_provider_result_claimed,
            "automatic_classification": self.automatic_classification,
            "automatic_classification_claimed": self.automatic_classification_claimed,
            "browser_automation_claimed": self.browser_automation_claimed,
            "browser_capture_claimed": self.browser_capture_claimed,
            "downloaded_media_claimed": self.downloaded_media_claimed,
            "extension_automation_claimed": self.extension_automation_claimed,
            "file_summaries": [summary.to_dict() for summary in self.file_summaries],
            "importer_name": self.importer_name,
            "importer_source": self.importer_source,
            "input_count": self.input_count,
            "input_order": self.input_order,
            "live_verification_claimed": self.live_verification_claimed,
            "media_download_claimed": self.media_download_claimed,
            "network_actions_performed": self.network_actions_performed,
            "ocr_claimed": self.ocr_claimed,
            "provenance_status": self.provenance_status,
            "queue_items": list(self.queue_items),
            "queue_metadata_available": self.queue_metadata_available,
            "queue_metadata_requested": self.queue_metadata_requested,
            "queue_review_items": list(self.queue_review_items),
            "review_status": self.review_status,
            "scope": self.scope,
            "screenshot_claimed": self.screenshot_claimed,
            "screenshot_ocr_claimed": self.screenshot_ocr_claimed,
            "source_kind": self.source_kind,
            "source_platform": self.source_platform,
            "source_row_kind": self.source_row_kind,
            "summary_only_preview": self.summary_only_preview,
            "total_error_count": self.total_error_count,
            "total_parsed_record_count": self.total_parsed_record_count,
            "total_skipped_record_count": self.total_skipped_record_count,
            "total_warning_count": self.total_warning_count,
            "user_review_required": self.user_review_required,
        }


@dataclass(frozen=True)
class TwitterExporterQueueReviewDraft:
    draft_id: str
    draft_status: str
    input_count: int
    eligible_input_count: int
    rejected_input_count: int
    total_parsed_record_count: int
    total_skipped_record_count: int
    total_warning_count: int
    total_error_count: int
    queue_review_items: tuple[dict[str, Any], ...] = ()
    queue_items: tuple[dict[str, Any], ...] = ()
    rejected_files: tuple[dict[str, Any], ...] = ()
    source_platform: str = TWITTER_EXPORTER_SOURCE_PLATFORM
    source_kind: str = TWITTER_EXPORTER_SOURCE_KIND
    importer_name: str = TWITTER_EXPORTER_IMPORTER_NAME
    importer_source: str = TWITTER_EXPORTER_IMPORTER_SOURCE
    source_row_kind: str = TWITTER_EXPORTER_SOURCE_ROW_KIND
    review_status: str = TWITTER_EXPORTER_REVIEW_STATUS_USER_REVIEW_REQUIRED
    provenance_status: str = TWITTER_EXPORTER_PROVENANCE_USER_SUPPLIED_LOCAL_EXPORT
    user_review_required: bool = True
    summary_only_preview: bool = True
    queue_metadata_only: bool = True
    live_verification_claimed: bool = False
    api_capture_claimed: bool = False
    browser_capture_claimed: bool = False
    browser_automation_claimed: bool = False
    extension_automation_claimed: bool = False
    archive_claimed: bool = False
    archive_provider_result_claimed: bool = False
    screenshot_ocr_claimed: bool = False
    screenshot_claimed: bool = False
    ocr_claimed: bool = False
    media_download_claimed: bool = False
    downloaded_media_claimed: bool = False
    automatic_classification_claimed: bool = False
    automatic_classification: bool = False
    evidence_files_completed_claimed: bool = False
    evidence_file_move_claimed: bool = False
    network_actions_performed: str = "none"
    schema_version: str = TWITTER_EXPORTER_QUEUE_DRAFT_SCHEMA_VERSION
    scope: str = TWITTER_EXPORTER_QUEUE_HANDOFF_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "api_capture_claimed": self.api_capture_claimed,
            "archive_claimed": self.archive_claimed,
            "archive_provider_result_claimed": self.archive_provider_result_claimed,
            "automatic_classification": self.automatic_classification,
            "automatic_classification_claimed": self.automatic_classification_claimed,
            "browser_automation_claimed": self.browser_automation_claimed,
            "browser_capture_claimed": self.browser_capture_claimed,
            "downloaded_media_claimed": self.downloaded_media_claimed,
            "draft_id": self.draft_id,
            "draft_status": self.draft_status,
            "eligible_input_count": self.eligible_input_count,
            "evidence_file_move_claimed": self.evidence_file_move_claimed,
            "evidence_files_completed_claimed": self.evidence_files_completed_claimed,
            "extension_automation_claimed": self.extension_automation_claimed,
            "importer_name": self.importer_name,
            "importer_source": self.importer_source,
            "input_count": self.input_count,
            "live_verification_claimed": self.live_verification_claimed,
            "media_download_claimed": self.media_download_claimed,
            "network_actions_performed": self.network_actions_performed,
            "ocr_claimed": self.ocr_claimed,
            "provenance_status": self.provenance_status,
            "queue_items": list(self.queue_items),
            "queue_metadata_only": self.queue_metadata_only,
            "queue_review_items": list(self.queue_review_items),
            "rejected_files": list(self.rejected_files),
            "rejected_input_count": self.rejected_input_count,
            "review_status": self.review_status,
            "schema_version": self.schema_version,
            "scope": self.scope,
            "screenshot_claimed": self.screenshot_claimed,
            "screenshot_ocr_claimed": self.screenshot_ocr_claimed,
            "source_kind": self.source_kind,
            "source_platform": self.source_platform,
            "source_row_kind": self.source_row_kind,
            "summary_only_preview": self.summary_only_preview,
            "total_error_count": self.total_error_count,
            "total_parsed_record_count": self.total_parsed_record_count,
            "total_skipped_record_count": self.total_skipped_record_count,
            "total_warning_count": self.total_warning_count,
            "user_review_required": self.user_review_required,
        }


def _queue_review_metadata_from_summary(
    summary: TwitterExporterSourceImportFileSummary,
) -> dict[str, Any]:
    item_id = _stable_id(
        "twitter_exporter_queue_draft_item",
        {
            "import_bundle_id": summary.import_bundle_id,
            "input_file_name": summary.input_file_name,
            "input_file_sha256": summary.input_file_sha256,
            "input_index": summary.input_index,
            "schema_version": TWITTER_EXPORTER_QUEUE_DRAFT_SCHEMA_VERSION,
        },
    )
    return {
        "api_capture_claimed": False,
        "archive_member_count": summary.archive_member_count,
        "archive_provider_result_claimed": False,
        "automatic_classification": False,
        "browser_automation_claimed": False,
        "downloaded_media_claimed": False,
        "evidence_file_move_claimed": False,
        "evidence_files_completed_claimed": False,
        "extension_automation_claimed": False,
        "import_bundle_id": summary.import_bundle_id,
        "import_status": summary.import_status,
        "importer_name": summary.importer_name,
        "importer_source": summary.importer_source,
        "input_file_name": summary.input_file_name,
        "input_file_sha256": summary.input_file_sha256,
        "input_file_size_bytes": summary.input_file_size_bytes,
        "input_index": summary.input_index,
        "item_id": item_id,
        "live_verification_claimed": False,
        "local_path": "",
        "media_download_claimed": False,
        "ocr_claimed": False,
        "parsed_record_count": summary.parsed_record_count,
        "provenance_status": summary.provenance_status,
        "queue_status": TWITTER_EXPORTER_REVIEW_STATUS_USER_REVIEW_REQUIRED,
        "review_status": summary.review_status,
        "schema_version": TWITTER_EXPORTER_QUEUE_DRAFT_SCHEMA_VERSION,
        "screenshot_claimed": False,
        "screenshot_ocr_claimed": False,
        "skipped_record_count": summary.skipped_record_count,
        "source_kind": summary.source_kind,
        "source_platform": summary.source_platform,
        "source_row_kind": summary.source_row_kind,
        "summary_only_preview": True,
        "user_review_required": True,
        "validation_error_count": summary.validation_error_count,
        "warning_count": summary.warning_count,
        "warnings": list(summary.warnings),
    }


def _evidence_queue_item_from_review_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    item = EvidenceQueueItem(
        item_id=str(metadata["item_id"]),
        item_role=EvidenceItemRole.MANUAL_EVIDENCE_NOTE,
        display_name=f"Twitter/X exporter review draft: {metadata['input_file_name']}",
        local_path="",
        file_hash=str(metadata["input_file_sha256"]),
        file_size_bytes=int(metadata["input_file_size_bytes"]),
        is_manual_import=True,
        item_status=EvidenceItemStatus.NEEDS_REVIEW,
        created_at_utc="",
        updated_at_utc="",
        user_notes=_stable_json(metadata),
    )
    return item.to_dict()


def build_twitter_exporter_queue_review_draft(
    state: TwitterExporterSourceImportReviewState,
) -> TwitterExporterQueueReviewDraft:
    eligible = tuple(summary for summary in state.file_summaries if summary.status == "ok")
    rejected = tuple(summary for summary in state.file_summaries if summary.status != "ok")
    review_items = tuple(_queue_review_metadata_from_summary(summary) for summary in eligible)
    queue_items = tuple(_evidence_queue_item_from_review_metadata(item) for item in review_items)
    rejected_files = tuple(
        {
            "input_file_name": summary.input_file_name,
            "input_index": summary.input_index,
            "status": summary.status,
            "validation_error_count": summary.validation_error_count,
            "validation_errors": list(summary.validation_errors),
        }
        for summary in rejected
    )
    draft_id = _stable_id(
        "twitter_exporter_queue_draft",
        {
            "eligible_item_ids": tuple(item["item_id"] for item in review_items),
            "input_count": state.input_count,
            "schema_version": TWITTER_EXPORTER_QUEUE_DRAFT_SCHEMA_VERSION,
            "total_error_count": state.total_error_count,
        },
    )
    return TwitterExporterQueueReviewDraft(
        draft_id=draft_id,
        draft_status="USER_REVIEW_REQUIRED" if review_items else "NO_QUEUE_DRAFT_CREATED",
        input_count=state.input_count,
        eligible_input_count=len(eligible),
        rejected_input_count=len(rejected),
        total_parsed_record_count=state.total_parsed_record_count,
        total_skipped_record_count=state.total_skipped_record_count,
        total_warning_count=state.total_warning_count,
        total_error_count=state.total_error_count,
        queue_review_items=review_items,
        queue_items=queue_items,
        rejected_files=rejected_files,
    )


def build_twitter_exporter_queue_review_draft_summary(
    draft: TwitterExporterQueueReviewDraft,
) -> str:
    return "\n".join(
        [
            "Twitter/X exporter queue review draft",
            f"Draft status: {draft.draft_status}",
            f"Review status: {draft.review_status}",
            f"Provenance: {draft.provenance_status}",
            f"Inputs: {draft.input_count}",
            f"Eligible queue draft items: {draft.eligible_input_count}",
            f"Rejected inputs: {draft.rejected_input_count}",
            f"Parsed records: {draft.total_parsed_record_count}",
            f"Skipped records: {draft.total_skipped_record_count}",
            f"Warnings: {draft.total_warning_count}",
            f"Errors: {draft.total_error_count}",
            "Queue metadata only: yes",
            "Network actions performed: none",
            "Live/API/browser/extension/archive/download/OCR/classification/evidence-completion claims: none",
        ]
    )


def _file_summary_from_cli_result(
    item: dict[str, Any],
    *,
    queue_metadata_available: bool,
) -> TwitterExporterSourceImportFileSummary:
    return TwitterExporterSourceImportFileSummary(
        input_index=int(item["input_index"]),
        input_file_name=str(item["input_name"]),
        status=str(item["status"]),
        import_bundle_id=str(item.get("import_bundle_id", "")),
        import_status=str(item.get("import_status", "")),
        input_file_sha256=str(item.get("local_file_sha256", "")),
        input_file_size_bytes=int(item.get("local_file_size_bytes", 0)),
        archive_member_count=int(item.get("archive_member_count", 0)),
        parsed_record_count=int(item.get("parsed_record_count", 0)),
        skipped_record_count=int(item.get("skipped_record_count", 0)),
        warning_count=int(item.get("warning_count", 0)),
        validation_error_count=len(item.get("validation_errors", ())),
        warnings=tuple(item.get("warnings", ())),
        validation_errors=tuple(item.get("validation_errors", ())),
        queue_metadata_available=queue_metadata_available and item["status"] == "ok",
    )


def build_twitter_exporter_source_review_state(
    *,
    input_paths: Sequence[str],
    as_queue_metadata: bool = False,
    max_zip_entries: int = 5000,
    max_total_uncompressed_bytes: int = 250 * 1024 * 1024,
    max_single_file_bytes: int = 50 * 1024 * 1024,
) -> TwitterExporterSourceImportReviewState:
    cli_result = build_twitter_exporter_import_cli_result(
        input_paths=input_paths,
        as_queue_metadata=as_queue_metadata,
        max_zip_entries=max_zip_entries,
        max_total_uncompressed_bytes=max_total_uncompressed_bytes,
        max_single_file_bytes=max_single_file_bytes,
    )
    file_summaries = tuple(
        _file_summary_from_cli_result(
            item,
            queue_metadata_available=as_queue_metadata,
        )
        for item in cli_result["results"]
    )
    return TwitterExporterSourceImportReviewState(
        file_summaries=file_summaries,
        input_count=int(cli_result["file_count"]),
        total_parsed_record_count=int(cli_result["total_parsed_record_count"]),
        total_skipped_record_count=int(cli_result["total_skipped_record_count"]),
        total_warning_count=int(cli_result["total_warning_count"]),
        total_error_count=int(cli_result["total_error_count"]),
        queue_review_items=tuple(cli_result["queue_review_items"]),
        queue_items=tuple(cli_result["queue_items"]),
        queue_metadata_requested=as_queue_metadata,
        queue_metadata_available=bool(cli_result["queue_review_items"]),
    )


def preview_twitter_exporter_local_import_source(
    input_paths: Sequence[str],
    *,
    as_queue_metadata: bool = False,
    max_zip_entries: int = 5000,
    max_total_uncompressed_bytes: int = 250 * 1024 * 1024,
    max_single_file_bytes: int = 50 * 1024 * 1024,
) -> TwitterExporterSourceImportReviewState:
    return build_twitter_exporter_source_review_state(
        input_paths=input_paths,
        as_queue_metadata=as_queue_metadata,
        max_zip_entries=max_zip_entries,
        max_total_uncompressed_bytes=max_total_uncompressed_bytes,
        max_single_file_bytes=max_single_file_bytes,
    )


def import_twitter_exporter_local_paths_for_review(
    input_paths: Sequence[str],
    *,
    as_queue_metadata: bool = False,
    max_zip_entries: int = 5000,
    max_total_uncompressed_bytes: int = 250 * 1024 * 1024,
    max_single_file_bytes: int = 50 * 1024 * 1024,
) -> TwitterExporterSourceImportReviewState:
    return preview_twitter_exporter_local_import_source(
        input_paths,
        as_queue_metadata=as_queue_metadata,
        max_zip_entries=max_zip_entries,
        max_total_uncompressed_bytes=max_total_uncompressed_bytes,
        max_single_file_bytes=max_single_file_bytes,
    )


def build_twitter_exporter_source_row_summary(
    state: TwitterExporterSourceImportReviewState,
) -> str:
    lines = [
        "Twitter/X exporter local import",
        f"Review status: {state.review_status}",
        f"Provenance: {state.provenance_status}",
        f"Files: {state.input_count}",
        f"Parsed records: {state.total_parsed_record_count}",
        f"Skipped records: {state.total_skipped_record_count}",
        f"Warnings: {state.total_warning_count}",
        f"Errors: {state.total_error_count}",
        f"Queue metadata available: {'yes' if state.queue_metadata_available else 'no'}",
        "Network actions performed: none",
        "Live/API/browser/extension/archive/download/OCR/classification claims: none",
    ]
    for summary in state.file_summaries:
        if summary.status == "ok":
            lines.append(
                "- "
                f"{summary.input_file_name}: {summary.parsed_record_count} record(s), "
                f"{summary.archive_member_count} archive member(s), "
                f"{summary.warning_count} warning(s), "
                f"sha256 {summary.input_file_sha256}"
            )
        else:
            lines.append(f"- {summary.input_file_name}: error")
            for error in summary.validation_errors:
                lines.append(f"  error: {error}")
    return "\n".join(lines)


def twitter_exporter_source_review_state_to_json(
    state: TwitterExporterSourceImportReviewState,
) -> str:
    return json.dumps(state.to_dict(), indent=2, sort_keys=True)


__all__ = [
    "TWITTER_EXPORTER_SOURCE_IMPORT_SCOPE",
    "TWITTER_EXPORTER_SOURCE_ROW_KIND",
    "TwitterExporterSourceImportFileSummary",
    "TwitterExporterSourceImportReviewState",
    "TwitterExporterQueueReviewDraft",
    "TWITTER_EXPORTER_QUEUE_DRAFT_SCHEMA_VERSION",
    "TWITTER_EXPORTER_QUEUE_HANDOFF_SCOPE",
    "build_twitter_exporter_queue_review_draft",
    "build_twitter_exporter_queue_review_draft_summary",
    "build_twitter_exporter_source_review_state",
    "build_twitter_exporter_source_row_summary",
    "import_twitter_exporter_local_paths_for_review",
    "preview_twitter_exporter_local_import_source",
    "twitter_exporter_source_review_state_to_json",
]
