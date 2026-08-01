from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Sequence

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
TWITTER_EXPORTER_SOURCE_IMPORT_SCOPE = (
    "Twitter/X exporter source-workflow local import preview only; explicit local files "
    "only; no X/Twitter API, browser capture, browser automation, extension automation, "
    "network, archive, download, screenshot/OCR, credential, broad folder scan, "
    "evidence file move, or automatic classification behavior"
)


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
    "build_twitter_exporter_source_review_state",
    "build_twitter_exporter_source_row_summary",
    "import_twitter_exporter_local_paths_for_review",
    "preview_twitter_exporter_local_import_source",
    "twitter_exporter_source_review_state_to_json",
]
