from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from total_export_bundle_index_reconcile import (
    BUNDLE_RECONCILE_STATUS_PRESENT,
    BundleIndexReconciliationItem,
    BundleIndexReconciliationResult,
)
from total_export_evidence_manifest import (
    build_evidence_manifest,
    build_evidence_manifest_markdown,
    build_evidence_manifest_text,
    evidence_manifest_to_dict,
)
from total_export_local_media import build_local_media_record
from total_export_local_media_verify import (
    LOCAL_MEDIA_VERIFY_STATUS_MISSING_LOCAL_FILE,
    LOCAL_MEDIA_VERIFY_STATUS_SHA256_MISMATCH,
    LOCAL_MEDIA_VERIFY_STATUS_SIZE_MISMATCH,
    LocalMediaVerificationItem,
    LocalMediaVerificationResult,
)
from total_export_manual_archive import build_manual_archive_record


FORMAT_MARKDOWN = "markdown"
FORMAT_TEXT = "text"
FORMAT_JSON = "json"
OUTPUT_FORMATS = (FORMAT_MARKDOWN, FORMAT_TEXT, FORMAT_JSON)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _as_dict(value: object, field_name: str) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    raise ValueError(f"{field_name} entries must be objects.")


def _as_list(value: object, field_name: str) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    raise ValueError(f"{field_name} must be a list.")


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    return tuple(_clean(item) for item in _as_list(value, field_name) if _clean(item))


def _integer(value: object, field_name: str) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc


def _boolean(value: object, field_name: str, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be true or false.")


def load_evidence_manifest_input(input_path: str) -> dict[str, object]:
    path = Path(input_path)
    if not path.is_file():
        raise ValueError(f"Evidence manifest input file does not exist: {input_path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid evidence manifest JSON: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Evidence manifest input could not be read: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Evidence manifest JSON must be an object.")
    return data


def _manual_archive_records(data: dict[str, object]):
    records = []
    for value in _as_list(data.get("manual_archive_records"), "manual_archive_records"):
        item = _as_dict(value, "manual_archive_records")
        records.append(
            build_manual_archive_record(
                source_url=_clean(item.get("source_url")),
                normalized_url=_clean(item.get("normalized_url")),
                archive_url=_clean(item.get("archive_url")),
                archive_service_name=_clean(item.get("archive_service_name")),
                archive_capture_time=_clean(item.get("archive_capture_time")),
                archive_status=_clean(item.get("archive_status")),
                archive_notes=_clean(item.get("archive_notes")),
                entered_at_utc=_clean(item.get("entered_at_utc")),
                verified_by_user_at_utc=_clean(item.get("verified_by_user_at_utc")),
            )
        )
    return tuple(records)


def _local_media_records(data: dict[str, object]):
    records = []
    for value in _as_list(data.get("local_media_records"), "local_media_records"):
        item = _as_dict(value, "local_media_records")
        records.append(
            build_local_media_record(
                source_url=_clean(item.get("source_url")),
                normalized_url=_clean(item.get("normalized_url")),
                package_id=_clean(item.get("package_id")),
                local_media_path=_clean(item.get("local_media_path")),
                local_media_filename=_clean(item.get("local_media_filename")),
                local_file_size_bytes=_integer(
                    item.get("local_file_size_bytes"), "local_file_size_bytes"
                ),
                local_file_sha256=_clean(item.get("local_file_sha256")),
                media_type=_clean(item.get("media_type")),
                duration_seconds=item.get("duration_seconds"),
                media_notes=_clean(item.get("media_notes")),
                registered_at_utc=_clean(item.get("registered_at_utc")),
                verified_at_utc=_clean(item.get("verified_at_utc")),
                exists_at_registration=_boolean(
                    item.get("exists_at_registration"),
                    "exists_at_registration",
                    default=False,
                ),
                hash_algorithm=_clean(item.get("hash_algorithm")),
                status=_clean(item.get("status")),
                inspect_local_file=False,
                compute_hash=False,
            )
        )
    return tuple(records)


def _local_media_verification_result(
    data: dict[str, object],
) -> LocalMediaVerificationResult | None:
    raw_items = _as_list(
        data.get("local_media_verification_items"),
        "local_media_verification_items",
    )
    if not raw_items:
        return None
    items = []
    for value in raw_items:
        item = _as_dict(value, "local_media_verification_items")
        items.append(
            LocalMediaVerificationItem(
                source_url=_clean(item.get("source_url")),
                normalized_url=_clean(item.get("normalized_url")),
                package_id=_clean(item.get("package_id")),
                local_media_path=_clean(item.get("local_media_path")),
                recorded_exists_at_registration=_boolean(
                    item.get("recorded_exists_at_registration"),
                    "recorded_exists_at_registration",
                    default=False,
                ),
                current_exists=_boolean(
                    item.get("current_exists"), "current_exists", default=False
                ),
                recorded_size_bytes=_integer(
                    item.get("recorded_size_bytes"), "recorded_size_bytes"
                ),
                current_size_bytes=_integer(
                    item.get("current_size_bytes"), "current_size_bytes"
                ),
                recorded_sha256=_clean(item.get("recorded_sha256")),
                current_sha256=_clean(item.get("current_sha256")),
                size_matches=_boolean(item.get("size_matches"), "size_matches", default=False),
                sha256_matches=_boolean(
                    item.get("sha256_matches"), "sha256_matches", default=False
                ),
                media_type=_clean(item.get("media_type")),
                status=_clean(item.get("status")),
                warnings=_string_tuple(item.get("warnings"), "warnings"),
                recommended_actions=_string_tuple(
                    item.get("recommended_actions"), "recommended_actions"
                ),
            )
        )
    item_tuple = tuple(items)
    return LocalMediaVerificationResult(
        record_count=len(item_tuple),
        checked_count=len(item_tuple),
        missing_count=sum(
            item.status == LOCAL_MEDIA_VERIFY_STATUS_MISSING_LOCAL_FILE for item in item_tuple
        ),
        size_mismatch_count=sum(
            item.status == LOCAL_MEDIA_VERIFY_STATUS_SIZE_MISMATCH for item in item_tuple
        ),
        sha256_mismatch_count=sum(
            item.status == LOCAL_MEDIA_VERIFY_STATUS_SHA256_MISMATCH for item in item_tuple
        ),
        items=item_tuple,
    )


def _bundle_item(value: object, field_name: str) -> BundleIndexReconciliationItem:
    item = _as_dict(value, field_name)
    status = _clean(item.get("status"))
    return BundleIndexReconciliationItem(
        expected_zip_path=_clean(item.get("expected_zip_path")),
        matched_zip_path=_clean(item.get("matched_zip_path")),
        zip_filename=_clean(item.get("zip_filename")),
        package_id=_clean(item.get("package_id")),
        source_url=_clean(item.get("source_url")),
        expected_present=_boolean(
            item.get("expected_present"), "expected_present", default=False
        ),
        index_status=_clean(item.get("index_status")),
        sidecar_ok=_boolean(item.get("sidecar_ok"), "sidecar_ok", default=False),
        needs_follow_up=_boolean(
            item.get("needs_follow_up"),
            "needs_follow_up",
            default=status != BUNDLE_RECONCILE_STATUS_PRESENT,
        ),
        status=status,
        notes=_clean(item.get("notes")),
        warnings=_string_tuple(item.get("warnings"), "warnings"),
        recommended_actions=_string_tuple(
            item.get("recommended_actions"), "recommended_actions"
        ),
    )


def _bundle_reconciliation_result(
    data: dict[str, object],
) -> BundleIndexReconciliationResult | None:
    item_values = _as_list(
        data.get("bundle_reconciliation_items"), "bundle_reconciliation_items"
    )
    unexpected_values = _as_list(
        data.get("unexpected_bundle_reconciliation_items"),
        "unexpected_bundle_reconciliation_items",
    )
    if not item_values and not unexpected_values:
        return None
    items = tuple(
        _bundle_item(value, "bundle_reconciliation_items") for value in item_values
    )
    unexpected_items = tuple(
        _bundle_item(value, "unexpected_bundle_reconciliation_items")
        for value in unexpected_values
    )
    return BundleIndexReconciliationResult(
        index_root_path=_clean(data.get("bundle_index_root_path")),
        expected_count=len(items),
        present_expected_count=sum(item.expected_present for item in items),
        missing_expected_count=sum(not item.expected_present for item in items),
        unexpected_zip_count=len(unexpected_items),
        needs_follow_up_count=sum(item.needs_follow_up for item in (*items, *unexpected_items)),
        items=items,
        unexpected_items=unexpected_items,
    )


def build_evidence_manifest_from_input_data(data: dict[str, object]):
    source_urls = tuple(
        _clean(value) for value in _as_list(data.get("source_urls"), "source_urls")
        if _clean(value)
    )
    return build_evidence_manifest(
        source_urls=source_urls,
        manual_archive_records=_manual_archive_records(data),
        local_media_records=_local_media_records(data),
        local_media_verification_result=_local_media_verification_result(data),
        bundle_reconciliation_result=_bundle_reconciliation_result(data),
    )


def render_evidence_manifest(result, output_format: str) -> str:
    if output_format == FORMAT_TEXT:
        return build_evidence_manifest_text(result)
    if output_format == FORMAT_JSON:
        return json.dumps(evidence_manifest_to_dict(result), indent=2, sort_keys=True)
    return build_evidence_manifest_markdown(result)


def write_output_file(output_path: str, text: str, *, overwrite: bool = False) -> str:
    path = Path(output_path)
    if path.exists() and not overwrite:
        raise ValueError(f"Output file already exists: {output_path}. Use --overwrite to replace it.")
    path.write_text(text, encoding="utf-8")
    return str(path)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a local metadata-only evidence package manifest."
    )
    parser.add_argument("--input", required=True, help="Local evidence manifest JSON input path.")
    parser.add_argument(
        "--format",
        choices=OUTPUT_FORMATS,
        default=FORMAT_MARKDOWN,
        help="Output format: markdown, text, or json.",
    )
    parser.add_argument("--output", default="", help="Optional output file path.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing output file.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        data = load_evidence_manifest_input(args.input)
        result = build_evidence_manifest_from_input_data(data)
        rendered = render_evidence_manifest(result, args.format)
        if args.output:
            write_output_file(args.output, rendered, overwrite=args.overwrite)
        else:
            print(rendered)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
