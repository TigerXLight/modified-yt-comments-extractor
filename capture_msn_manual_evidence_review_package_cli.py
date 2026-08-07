from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from capture_msn_manual_evidence_review_package import (
    MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_STATUS_PENDING,
    build_msn_manual_evidence_review_package,
    msn_manual_evidence_review_package_to_json,
)
from capture_msn_manual_evidence_review_package_store import (
    msn_manual_evidence_review_package_store_report_to_json,
    store_msn_manual_evidence_review_package,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build/store an MSN manual Evidence Review package from an explicit queue JSON report.")
    parser.add_argument("--queue-json", required=True, help="Explicit MSN manual Evidence Queue JSON report file.")
    parser.add_argument("--output-dir", required=True, help="Directory where package/index JSON files will be written.")
    parser.add_argument("--reviewer-id", default="operator")
    parser.add_argument("--review-status", default=MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_STATUS_PENDING)
    parser.add_argument("--note", action="append", default=[])
    parser.add_argument("--print-package-json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    queue_path = Path(args.queue_json)
    queue_report = json.loads(queue_path.read_text(encoding="utf-8"))
    package = build_msn_manual_evidence_review_package(
        queue_report,
        reviewer_id=args.reviewer_id,
        review_status=args.review_status,
        notes=args.note,
    )
    store_report = store_msn_manual_evidence_review_package(package, args.output_dir)
    if args.print_package_json:
        sys.stdout.write(msn_manual_evidence_review_package_to_json(package))
    else:
        sys.stdout.write(msn_manual_evidence_review_package_store_report_to_json(store_report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
