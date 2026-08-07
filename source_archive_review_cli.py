from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from source_archive_review import build_source_archive_review, dump_json, load_json_file
from source_archive_review_store import store_source_archive_review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a shared archive review package from archive result intake output.")
    parser.add_argument("--archive-result-intake-json", required=True, help="Path to source archive result intake record JSON.")
    parser.add_argument("--archive-receipt-index-json", help="Optional path to source archive receipt index JSON.")
    parser.add_argument("--archive-review-handoff-json", help="Optional path to source archive review handoff JSON.")
    parser.add_argument("--decision", default="APPROVED", choices=["APPROVED", "REJECTED", "REVISION_REQUESTED"], help="Manual archive review decision.")
    parser.add_argument("--reviewer-id", default="manual_archive_reviewer", help="Non-secret reviewer identifier.")
    parser.add_argument("--review-note", action="append", default=[], help="Optional review note; may be repeated.")
    parser.add_argument("--output-dir", required=True, help="Directory where output JSON files will be written.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    outputs = build_source_archive_review(
        archive_result_intake_record=load_json_file(args.archive_result_intake_json),
        archive_receipt_index=load_json_file(args.archive_receipt_index_json) if args.archive_receipt_index_json else None,
        archive_review_handoff=load_json_file(args.archive_review_handoff_json) if args.archive_review_handoff_json else None,
        decision=args.decision,
        reviewer_id=args.reviewer_id,
        review_notes=args.review_note,
    )
    receipt = store_source_archive_review(outputs.as_dict(), Path(args.output_dir))
    print(dump_json(receipt), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
