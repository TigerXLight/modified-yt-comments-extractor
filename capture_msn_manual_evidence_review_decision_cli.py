from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from capture_msn_manual_evidence_review_decision import (
    MSN_MANUAL_EVIDENCE_REVIEW_DECISION_APPROVED,
    MSN_MANUAL_EVIDENCE_REVIEW_DECISIONS,
    build_msn_manual_evidence_review_decision,
    msn_manual_evidence_review_decision_to_json,
)
from capture_msn_manual_evidence_review_decision_store import (
    msn_manual_evidence_review_decision_store_report_to_json,
    store_msn_manual_evidence_review_decision,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Record/store an MSN manual Evidence Review decision from an explicit review package JSON.")
    parser.add_argument("--review-package-json", required=True, help="Explicit MSN manual Evidence Review package JSON file.")
    parser.add_argument("--output-dir", required=True, help="Directory where decision/update JSON files will be written.")
    parser.add_argument("--decision", default=MSN_MANUAL_EVIDENCE_REVIEW_DECISION_APPROVED, choices=sorted(MSN_MANUAL_EVIDENCE_REVIEW_DECISIONS))
    parser.add_argument("--reviewer-id", default="operator")
    parser.add_argument("--completed-action", action="append", default=[])
    parser.add_argument("--comment", action="append", default=[])
    parser.add_argument("--print-decision-json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    review_package = json.loads(Path(args.review_package_json).read_text(encoding="utf-8"))
    decision = build_msn_manual_evidence_review_decision(
        review_package,
        review_decision=args.decision,
        reviewer_id=args.reviewer_id,
        completed_action_ids=args.completed_action,
        comments=args.comment,
    )
    store_report = store_msn_manual_evidence_review_decision(decision, args.output_dir)
    if args.print_decision_json:
        sys.stdout.write(msn_manual_evidence_review_decision_to_json(decision))
    else:
        sys.stdout.write(msn_manual_evidence_review_decision_store_report_to_json(store_report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
