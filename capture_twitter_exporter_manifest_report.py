from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from capture_twitter_exporter_source_import import TwitterExporterQueueReviewDraft
from total_export_manifest import TotalExportManifest, safe_package_id


TWITTER_EXPORTER_MANIFEST_REPORT_SCHEMA_VERSION = "twitter_exporter_manifest_report.v1"
TWITTER_EXPORTER_MANIFEST_REPORT_SCOPE = (
    "Twitter/X exporter queue draft to export manifest/report review metadata only; "
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
class TwitterExporterManifestReviewEntry:
    entry_id: str
    queue_draft_item_id: str
    input_file_name: str
    input_file_sha256: str
    input_file_size_bytes: int
    parsed_record_count: int
    skipped_record_count: int
    warning_count: int
    error_count: int
    archive_member_count: int
    import_bundle_id: str = ""
    import_status: str = ""
    entry_kind: str = "twitter_x_local_exporter_review_draft"
    importer_name: str = "Twitter Exporter"
    importer_source: str = "twitter_exporter_user_supplied_local_file"
    source_platform: str = "twitter_x"
    source_kind: str = "local_export"
    review_status: str = "USER_REVIEW_REQUIRED"
    provenance_status: str = "USER_SUPPLIED_LOCAL_EXPORT"
    user_review_required: bool = True
    summary_only: bool = True
    manifest_metadata_only: bool = True
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
    schema_version: str = TWITTER_EXPORTER_MANIFEST_REPORT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TwitterExporterManifestReport:
    report_id: str
    entries: tuple[TwitterExporterManifestReviewEntry, ...]
    rejected_input_count: int
    input_count: int
    total_parsed_record_count: int
    total_skipped_record_count: int
    total_warning_count: int
    total_error_count: int
    review_status: str = "USER_REVIEW_REQUIRED"
    provenance_status: str = "USER_SUPPLIED_LOCAL_EXPORT"
    summary_only: bool = True
    manifest_metadata_only: bool = True
    no_entries_reason: str = ""
    schema_version: str = TWITTER_EXPORTER_MANIFEST_REPORT_SCHEMA_VERSION
    scope: str = TWITTER_EXPORTER_MANIFEST_REPORT_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "input_count": self.input_count,
            "manifest_metadata_only": self.manifest_metadata_only,
            "no_entries_reason": self.no_entries_reason,
            "provenance_status": self.provenance_status,
            "rejected_input_count": self.rejected_input_count,
            "report_id": self.report_id,
            "review_status": self.review_status,
            "schema_version": self.schema_version,
            "scope": self.scope,
            "summary_only": self.summary_only,
            "total_error_count": self.total_error_count,
            "total_parsed_record_count": self.total_parsed_record_count,
            "total_skipped_record_count": self.total_skipped_record_count,
            "total_warning_count": self.total_warning_count,
        }


def _entry_from_queue_review_item(item: dict[str, Any]) -> TwitterExporterManifestReviewEntry:
    queue_item_id = str(item.get("item_id", ""))
    input_file_name = str(item.get("input_file_name", ""))
    entry_id = _stable_id(
        "twitter_exporter_manifest_entry",
        {
            "input_file_name": input_file_name,
            "input_file_sha256": str(item.get("input_file_sha256", "")),
            "queue_draft_item_id": queue_item_id,
            "schema_version": TWITTER_EXPORTER_MANIFEST_REPORT_SCHEMA_VERSION,
        },
    )
    return TwitterExporterManifestReviewEntry(
        entry_id=entry_id,
        queue_draft_item_id=queue_item_id,
        input_file_name=input_file_name,
        input_file_sha256=str(item.get("input_file_sha256", "")),
        input_file_size_bytes=int(item.get("input_file_size_bytes", 0)),
        parsed_record_count=int(item.get("parsed_record_count", 0)),
        skipped_record_count=int(item.get("skipped_record_count", 0)),
        warning_count=int(item.get("warning_count", 0)),
        error_count=int(item.get("validation_error_count", 0)),
        archive_member_count=int(item.get("archive_member_count", 0)),
        import_bundle_id=str(item.get("import_bundle_id", "")),
        import_status=str(item.get("import_status", "")),
        importer_name=str(item.get("importer_name", "Twitter Exporter")),
        importer_source=str(item.get("importer_source", "twitter_exporter_user_supplied_local_file")),
        source_platform=str(item.get("source_platform", "twitter_x")),
        source_kind=str(item.get("source_kind", "local_export")),
        review_status=str(item.get("review_status", "USER_REVIEW_REQUIRED")),
        provenance_status=str(item.get("provenance_status", "USER_SUPPLIED_LOCAL_EXPORT")),
    )


def build_twitter_exporter_manifest_review_entries(
    draft: TwitterExporterQueueReviewDraft,
) -> tuple[TwitterExporterManifestReviewEntry, ...]:
    return tuple(
        _entry_from_queue_review_item(item)
        for item in sorted(
            draft.queue_review_items,
            key=lambda value: (str(value.get("input_file_name", "")), str(value.get("item_id", ""))),
        )
    )


def build_twitter_exporter_manifest_report(
    draft: TwitterExporterQueueReviewDraft,
) -> TwitterExporterManifestReport:
    entries = build_twitter_exporter_manifest_review_entries(draft)
    report_id = _stable_id(
        "twitter_exporter_manifest_report",
        {
            "draft_id": draft.draft_id,
            "entry_ids": tuple(entry.entry_id for entry in entries),
            "schema_version": TWITTER_EXPORTER_MANIFEST_REPORT_SCHEMA_VERSION,
        },
    )
    return TwitterExporterManifestReport(
        report_id=report_id,
        entries=entries,
        rejected_input_count=draft.rejected_input_count,
        input_count=draft.input_count,
        total_parsed_record_count=draft.total_parsed_record_count,
        total_skipped_record_count=draft.total_skipped_record_count,
        total_warning_count=draft.total_warning_count,
        total_error_count=draft.total_error_count,
        no_entries_reason="NO_QUEUE_DRAFT_CREATED" if not entries else "",
    )


def build_twitter_exporter_total_export_manifest(
    draft: TwitterExporterQueueReviewDraft,
    *,
    package_id: str = "",
) -> TotalExportManifest:
    report = build_twitter_exporter_manifest_report(draft)
    safe_id = safe_package_id(package_id or report.report_id)
    return TotalExportManifest(
        package_id=safe_id,
        created_at_utc="",
        source_urls=[],
        output_folder="",
        capture_options=["twitter_x_local_exporter_queue_review_draft"],
        assets=[],
        archive_results=[entry.to_dict() for entry in report.entries],
        notes=_stable_json(report.to_dict()),
    )


def build_twitter_exporter_manifest_report_text(
    draft: TwitterExporterQueueReviewDraft,
) -> str:
    report = build_twitter_exporter_manifest_report(draft)
    lines = [
        "Twitter/X exporter export manifest review metadata",
        f"Report ID: {report.report_id}",
        f"Review status: {report.review_status}",
        f"Provenance: {report.provenance_status}",
        f"Inputs: {report.input_count}",
        f"Entries: {len(report.entries)}",
        f"Rejected inputs: {report.rejected_input_count}",
        f"Parsed records: {report.total_parsed_record_count}",
        f"Skipped records: {report.total_skipped_record_count}",
        f"Warnings: {report.total_warning_count}",
        f"Errors: {report.total_error_count}",
        "Summary/counts only: yes",
        "Manifest metadata only: yes",
        "Network actions performed: none",
        "Live/API/browser/extension/archive/download/OCR/WARC/WACZ/classification/completed-evidence claims: none",
        "Entries:",
    ]
    if not report.entries:
        lines.append(f"- (none; {report.no_entries_reason or 'no eligible queue draft items'})")
    for entry in report.entries:
        lines.append(
            "- "
            f"{entry.input_file_name}: "
            f"{entry.parsed_record_count} parsed, "
            f"{entry.skipped_record_count} skipped, "
            f"{entry.warning_count} warning(s), "
            f"{entry.error_count} error(s), "
            f"{entry.archive_member_count} archive member(s), "
            f"sha256 {entry.input_file_sha256}"
        )
    return "\n".join(lines)


def twitter_exporter_manifest_report_to_json(report: TwitterExporterManifestReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)


__all__ = [
    "TWITTER_EXPORTER_MANIFEST_REPORT_SCHEMA_VERSION",
    "TWITTER_EXPORTER_MANIFEST_REPORT_SCOPE",
    "TwitterExporterManifestReport",
    "TwitterExporterManifestReviewEntry",
    "build_twitter_exporter_manifest_report",
    "build_twitter_exporter_manifest_report_text",
    "build_twitter_exporter_manifest_review_entries",
    "build_twitter_exporter_total_export_manifest",
    "twitter_exporter_manifest_report_to_json",
]
