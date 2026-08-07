from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from source_evidence_review import build_source_evidence_review, dump_json, load_json_file
from source_evidence_review_store import store_source_evidence_review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a shared source Evidence Review package and optional decision record.")
    parser.add_argument("--evidence-queue-item-json", required=True, help="Path to source Evidence Queue item JSON.")
    parser.add_argument("--evidence-review-handoff-json", help="Optional path to source Evidence Review handoff JSON.")
    parser.add_argument("--review-decision-json", help="Optional reviewer decision JSON; APPROVED, REJECTED, or REVISION_REQUESTED.")
    parser.add_argument("--decision", choices=["PENDING_DECISION", "APPROVED", "REJECTED", "REVISION_REQUESTED"], help="Inline review decision when no JSON file is supplied.")
    parser.add_argument("--reviewer-id", default="manual_reviewer", help="Non-secret reviewer/operator identifier.")
    parser.add_argument("--completed-action", action="append", default=[], help="Completed review action id; may be repeated.")
    parser.add_argument("--review-note", action="append", default=[], help="Optional review note; may be repeated.")
    parser.add_argument("--review-profile", default="source_adapter_shared_review_v1", help="Deterministic review profile label.")
    parser.add_argument("--output-dir", required=True, help="Directory where output JSON files will be written.")
    return parser


def _decision_from_args(args: argparse.Namespace) -> dict | None:
    if args.review_decision_json:
        decision = load_json_file(args.review_decision_json)
    elif args.decision:
        decision = {"decision": args.decision}
    else:
        return None
    decision.setdefault("reviewer_id", args.reviewer_id)
    if args.completed_action:
        decision["completed_action_ids"] = args.completed_action
    if args.review_note:
        decision["notes"] = args.review_note
    return decision


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    queue_item = load_json_file(args.evidence_queue_item_json)
    handoff = load_json_file(args.evidence_review_handoff_json) if args.evidence_review_handoff_json else None
    outputs = build_source_evidence_review(
        evidence_queue_item=queue_item,
        evidence_review_handoff=handoff,
        reviewer_decision=_decision_from_args(args),
        reviewer_id=args.reviewer_id,
        review_profile=args.review_profile,
        review_notes=args.review_note,
    )
    receipt = store_source_evidence_review(outputs.as_dict(), Path(args.output_dir))
    print(dump_json(receipt), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
