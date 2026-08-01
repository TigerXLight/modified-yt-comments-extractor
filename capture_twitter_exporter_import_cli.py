from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from capture_twitter_exporter_import import (
    TWITTER_EXPORTER_IMPORTER_NAME,
    TWITTER_EXPORTER_IMPORTER_SOURCE,
    TWITTER_EXPORTER_PROVENANCE_USER_SUPPLIED_LOCAL_EXPORT,
    TWITTER_EXPORTER_REVIEW_STATUS_USER_REVIEW_REQUIRED,
    build_twitter_exporter_queue_review_item,
    import_twitter_exporter_local_file,
)


TWITTER_EXPORTER_IMPORT_CLI_SCOPE = (
    "Twitter/X exporter local import CLI preview only; explicit local files only; "
    "no X/Twitter API, browser automation, extension automation, network, archive, "
    "download, screenshot/OCR, credential, broad folder scan, evidence file move, "
    "or automatic classification behavior"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview local Twitter/X exporter output files as review metadata.",
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="Explicit local Twitter/X exporter output file. Repeat for batch import.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print a safe summary preview. This is the default when --json is omitted.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print deterministic JSON summary metadata.",
    )
    parser.add_argument(
        "--as-queue-metadata",
        action="store_true",
        help="Include USER_REVIEW_REQUIRED queue review metadata in the result.",
    )
    parser.add_argument("--max-zip-entries", type=int, default=5000)
    parser.add_argument("--max-total-uncompressed-bytes", type=int, default=250 * 1024 * 1024)
    parser.add_argument("--max-single-file-bytes", type=int, default=50 * 1024 * 1024)
    return parser


def _safe_error(exc: Exception) -> str:
    return str(exc).replace("\\", "/")


def _bundle_summary(bundle: Any) -> dict[str, Any]:
    data = bundle.to_dict()
    return {
        "archive_member_count": data["archive_member_count"],
        "import_bundle_id": data["import_bundle_id"],
        "import_status": data["import_status"],
        "importer_name": data["importer_name"],
        "importer_source": data["importer_source"],
        "local_file_name": data["local_file_name"],
        "local_file_sha256": data["local_file_sha256"],
        "local_file_size_bytes": data["local_file_size_bytes"],
        "parsed_record_count": data["parsed_record_count"],
        "provenance_status": data["provenance_status"],
        "review_status": data["review_status"],
        "skipped_record_count": data["skipped_record_count"],
        "source_kind": data["source_kind"],
        "source_platform": data["source_platform"],
        "validation_error_count": len(data["validation_errors"]),
        "warning_count": len(data["warnings"]),
        "warnings": data["warnings"],
    }


def build_twitter_exporter_import_cli_result(
    *,
    input_paths: Sequence[str],
    as_queue_metadata: bool = False,
    max_zip_entries: int = 5000,
    max_total_uncompressed_bytes: int = 250 * 1024 * 1024,
    max_single_file_bytes: int = 50 * 1024 * 1024,
) -> dict[str, Any]:
    if not input_paths:
        raise ValueError("At least one --input file is required.")
    results: list[dict[str, Any]] = []
    queue_review_items: list[dict[str, Any]] = []
    queue_items: list[dict[str, Any]] = []
    total_parsed = 0
    total_skipped = 0
    warning_count = 0
    error_count = 0

    for index, raw_path in enumerate(input_paths, start=1):
        path = Path(raw_path)
        file_result: dict[str, Any] = {
            "input_index": index,
            "input_name": path.name,
            "status": "error",
            "validation_errors": [],
        }
        try:
            bundle = import_twitter_exporter_local_file(
                path,
                max_zip_entries=max_zip_entries,
                max_total_uncompressed_bytes=max_total_uncompressed_bytes,
                max_single_file_bytes=max_single_file_bytes,
            )
        except ValueError as exc:
            file_result["validation_errors"] = [_safe_error(exc)]
            error_count += 1
            results.append(file_result)
            continue

        summary = _bundle_summary(bundle)
        file_result.update(summary)
        file_result["status"] = "ok"
        results.append(file_result)
        total_parsed += int(summary["parsed_record_count"])
        total_skipped += int(summary["skipped_record_count"])
        warning_count += int(summary["warning_count"])
        if as_queue_metadata:
            review_item = build_twitter_exporter_queue_review_item(bundle)
            queue_review_items.append(review_item.to_dict())
            queue_items.append(review_item.to_evidence_queue_item().to_dict())

    result: dict[str, Any] = {
        "api_capture_claimed": False,
        "archive_provider_result_claimed": False,
        "automatic_classification": False,
        "browser_automation_claimed": False,
        "downloaded_media_claimed": False,
        "extension_automation_claimed": False,
        "file_count": len(input_paths),
        "importer_name": TWITTER_EXPORTER_IMPORTER_NAME,
        "importer_source": TWITTER_EXPORTER_IMPORTER_SOURCE,
        "input_order": "input_order_preserved",
        "live_verification_claimed": False,
        "network_actions_performed": "none",
        "ocr_claimed": False,
        "preview_only": True,
        "provenance_status": TWITTER_EXPORTER_PROVENANCE_USER_SUPPLIED_LOCAL_EXPORT,
        "queue_metadata_requested": as_queue_metadata,
        "queue_review_items": queue_review_items,
        "queue_items": queue_items,
        "review_status": TWITTER_EXPORTER_REVIEW_STATUS_USER_REVIEW_REQUIRED,
        "results": results,
        "scope": TWITTER_EXPORTER_IMPORT_CLI_SCOPE,
        "screenshot_claimed": False,
        "source_platform": "twitter_x",
        "total_error_count": error_count,
        "total_parsed_record_count": total_parsed,
        "total_skipped_record_count": total_skipped,
        "total_warning_count": warning_count,
        "user_review_required": True,
    }
    return result


def format_twitter_exporter_import_preview(result: dict[str, Any]) -> str:
    lines = [
        "Twitter/X exporter local import preview",
        f"Importer: {result['importer_name']}",
        f"Source platform: {result['source_platform']}",
        f"Review status: {result['review_status']}",
        f"Provenance: {result['provenance_status']}",
        f"Inputs: {result['file_count']}",
        f"Parsed records: {result['total_parsed_record_count']}",
        f"Skipped records: {result['total_skipped_record_count']}",
        f"Warnings: {result['total_warning_count']}",
        f"Errors: {result['total_error_count']}",
        f"Queue metadata items: {len(result['queue_review_items'])}",
        "Network actions performed: none",
        "API capture claimed: no",
        "Browser automation claimed: no",
        "Extension automation claimed: no",
        "Live verification claimed: no",
        "Automatic classification: no",
        "Files:",
    ]
    for item in result["results"]:
        if item["status"] == "ok":
            lines.extend(
                [
                    f"- {item['input_name']}: ok",
                    f"  sha256: {item['local_file_sha256']}",
                    f"  size_bytes: {item['local_file_size_bytes']}",
                    f"  archive_members: {item['archive_member_count']}",
                    f"  parsed_records: {item['parsed_record_count']}",
                    f"  skipped_records: {item['skipped_record_count']}",
                    f"  warnings: {item['warning_count']}",
                ]
            )
        else:
            lines.append(f"- {item['input_name']}: error")
            for error in item["validation_errors"]:
                lines.append(f"  error: {error}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = build_twitter_exporter_import_cli_result(
            input_paths=args.input,
            as_queue_metadata=args.as_queue_metadata,
            max_zip_entries=args.max_zip_entries,
            max_total_uncompressed_bytes=args.max_total_uncompressed_bytes,
            max_single_file_bytes=args.max_single_file_bytes,
        )
    except ValueError as exc:
        parser.error(str(exc))

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_twitter_exporter_import_preview(result))
    return 1 if result["total_error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
