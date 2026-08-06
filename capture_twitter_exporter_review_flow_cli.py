from __future__ import annotations

import argparse
import json
from typing import Any, Sequence

from capture_twitter_exporter_review_flow import (
    TwitterExporterLocalReviewFlow,
    build_twitter_exporter_local_review_flow,
    build_twitter_exporter_review_flow_summary,
)


TWITTER_EXPORTER_REVIEW_FLOW_CLI_SCOPE = (
    "Twitter/X exporter end-to-end local review flow CLI summary only; explicit "
    "local files only; no raw tweet text, record payloads, full local paths, live "
    "verification, API capture, browser automation, extension automation, archive, "
    "download, screenshot/OCR, WARC/WACZ, completed-evidence, evidence-file move, "
    "or automatic classification claims"
)
DEFAULT_REVIEW_FLOW_SESSION_ID = "session-twitter-exporter-review-flow-cli"
DEFAULT_REVIEW_FLOW_TIMESTAMP_UTC = "1970-01-01T00:00:00Z"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the local Twitter/X exporter review flow as safe summary metadata.",
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="Explicit local Twitter/X exporter output file. Repeat for batch flow review.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print deterministic JSON summary metadata.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output when --json is used.",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Return non-zero when any input produces a validation error.",
    )
    parser.add_argument(
        "--show-receipt-id",
        action="store_true",
        help="Include the receipt ID in text output.",
    )
    parser.add_argument(
        "--show-manifest-summary",
        action="store_true",
        help="Include the manifest/report subsection in text output.",
    )
    parser.add_argument(
        "--show-queue-summary",
        action="store_true",
        help="Include the queue draft subsection in text output.",
    )
    parser.add_argument("--session-id", default=DEFAULT_REVIEW_FLOW_SESSION_ID)
    parser.add_argument("--timestamp-utc", default=DEFAULT_REVIEW_FLOW_TIMESTAMP_UTC)
    parser.add_argument("--previous-event-hash", default="")
    parser.add_argument("--actor-id", default="")
    parser.add_argument("--app-version", default="")
    parser.add_argument("--max-zip-entries", type=int, default=5000)
    parser.add_argument("--max-total-uncompressed-bytes", type=int, default=250 * 1024 * 1024)
    parser.add_argument("--max-single-file-bytes", type=int, default=50 * 1024 * 1024)
    return parser


def build_twitter_exporter_review_flow_cli_result(
    *,
    input_paths: Sequence[str],
    session_id: str = DEFAULT_REVIEW_FLOW_SESSION_ID,
    timestamp_utc: str = DEFAULT_REVIEW_FLOW_TIMESTAMP_UTC,
    previous_event_hash: str = "",
    actor_id: str = "",
    app_version: str = "",
    max_zip_entries: int = 5000,
    max_total_uncompressed_bytes: int = 250 * 1024 * 1024,
    max_single_file_bytes: int = 50 * 1024 * 1024,
) -> dict[str, Any]:
    if not input_paths:
        raise ValueError("At least one --input file is required.")
    flow = build_twitter_exporter_local_review_flow(
        input_paths,
        session_id=session_id,
        timestamp_utc=timestamp_utc,
        previous_event_hash=previous_event_hash,
        actor_id=actor_id,
        app_version=app_version,
        max_zip_entries=max_zip_entries,
        max_total_uncompressed_bytes=max_total_uncompressed_bytes,
        max_single_file_bytes=max_single_file_bytes,
    )
    data = flow.to_dict()
    data["cli_scope"] = TWITTER_EXPORTER_REVIEW_FLOW_CLI_SCOPE
    data["network_actions_performed"] = "none"
    return data


def _safe_file_line(item: dict[str, Any]) -> str:
    return (
        "- "
        f"{item['input_file_name']}: "
        f"{item['status']}, "
        f"{item['parsed_record_count']} parsed, "
        f"{item['skipped_record_count']} skipped, "
        f"{item['warning_count']} warning(s), "
        f"{item['validation_error_count']} error(s), "
        f"{item['archive_member_count']} archive member(s), "
        f"sha256 {item['input_file_sha256']}"
    )


def format_twitter_exporter_review_flow_cli_summary(
    flow: TwitterExporterLocalReviewFlow,
    *,
    show_receipt_id: bool = False,
    show_manifest_summary: bool = False,
    show_queue_summary: bool = False,
) -> str:
    data = flow.to_dict()
    lines = [
        "Twitter/X exporter end-to-end local review flow",
        f"Flow ID: {data['flow_id']}",
        f"Status: {data['status']}",
        f"Review status: {data['review_status']}",
        f"Provenance: {data['provenance_status']}",
        f"Inputs: {data['input_count']}",
        f"Queue draft items: {data['queue_draft_summary']['eligible_input_count']}",
        f"Manifest/report entries: {data['manifest_report_summary']['entry_count']}",
        f"Action receipt result: {data['action_receipt_summary']['result']}",
        "Summary/counts only: yes",
        "Network actions performed: none",
        "Not live verified; not completed evidence.",
        "Live/API/browser/extension/archive/download/OCR/WARC/WACZ/classification/completed-evidence claims: none",
    ]
    if show_receipt_id:
        lines.append(f"Receipt ID: {data['action_receipt_summary']['receipt_id']}")
    lines.append("Files:")
    if not data["file_summaries"]:
        lines.append("- (none)")
    for item in data["file_summaries"]:
        lines.append(_safe_file_line(item))
    if show_queue_summary:
        queue = data["queue_draft_summary"]
        lines.extend(
            [
                "",
                "Queue draft summary:",
                f"- Draft status: {queue['draft_status']}",
                f"- Eligible inputs: {queue['eligible_input_count']}",
                f"- Rejected inputs: {queue['rejected_input_count']}",
                f"- Parsed records: {queue['total_parsed_record_count']}",
                f"- Errors: {queue['total_error_count']}",
            ]
        )
    if show_manifest_summary:
        manifest = data["manifest_report_summary"]
        lines.extend(
            [
                "",
                "Manifest/report summary:",
                f"- Report ID: {manifest['report_id']}",
                f"- Entries: {manifest['entry_count']}",
                f"- Parsed records: {manifest['total_parsed_record_count']}",
                f"- Errors: {manifest['total_error_count']}",
                f"- No entries reason: {manifest['no_entries_reason'] or '(none)'}",
            ]
        )
    return "\n".join(lines)


def _exit_code_for_result(result: dict[str, Any], *, fail_on_error: bool) -> int:
    total_errors = int(result["source_review_summary"]["total_error_count"])
    if result["status"] == "REVIEW_ERROR":
        return 1
    if fail_on_error and total_errors:
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        flow = build_twitter_exporter_local_review_flow(
            args.input,
            session_id=args.session_id,
            timestamp_utc=args.timestamp_utc,
            previous_event_hash=args.previous_event_hash,
            actor_id=args.actor_id,
            app_version=args.app_version,
            max_zip_entries=args.max_zip_entries,
            max_total_uncompressed_bytes=args.max_total_uncompressed_bytes,
            max_single_file_bytes=args.max_single_file_bytes,
        )
    except ValueError as exc:
        parser.error(str(exc))

    result = flow.to_dict()
    result["cli_scope"] = TWITTER_EXPORTER_REVIEW_FLOW_CLI_SCOPE
    if args.json:
        if args.pretty:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(
            format_twitter_exporter_review_flow_cli_summary(
                flow,
                show_receipt_id=args.show_receipt_id,
                show_manifest_summary=args.show_manifest_summary,
                show_queue_summary=args.show_queue_summary,
            )
        )
    return _exit_code_for_result(result, fail_on_error=args.fail_on_error)


if __name__ == "__main__":
    raise SystemExit(main())
