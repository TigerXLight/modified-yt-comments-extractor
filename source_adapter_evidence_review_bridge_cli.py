from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_evidence_review_bridge import build_source_adapter_evidence_review_bridge
from source_adapter_evidence_review_bridge_store import store_source_adapter_evidence_review_bridge


def _load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _decision_from_args(args: argparse.Namespace) -> dict | None:
    if args.review_decision_json:
        decision = _load_json(args.review_decision_json)
        if not isinstance(decision, dict):
            raise ValueError("review decision JSON must contain an object")
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
    parser = argparse.ArgumentParser(description="Build shared Adapter Evidence Review Bridge packages.")
    parser.add_argument("--evidence-queue-bridge-json", required=True, help="Adapter Evidence Queue Bridge package JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for bridge artifacts.")
    parser.add_argument("--review-decision-json", help="Optional batch/shared reviewer decision JSON.")
    parser.add_argument("--decision", choices=["PENDING_DECISION", "APPROVED", "REJECTED", "REVISION_REQUESTED"], help="Inline shared decision when no JSON file is supplied.")
    parser.add_argument("--reviewer-id", default="manual_reviewer", help="Non-secret reviewer/operator identifier.")
    parser.add_argument("--completed-action", action="append", default=[], help="Completed review action id; may be repeated.")
    parser.add_argument("--review-profile", default="source_adapter_shared_review_v1", help="Deterministic shared review profile.")
    parser.add_argument("--review-note", action="append", default=[], help="Optional review note; may be repeated.")
    args = parser.parse_args(argv)

    bridge = _load_json(args.evidence_queue_bridge_json)
    package = build_source_adapter_evidence_review_bridge(
        bridge,
        reviewer_decision=_decision_from_args(args),
        reviewer_id=args.reviewer_id,
        review_profile=args.review_profile,
        review_notes=args.review_note,
    )
    result = store_source_adapter_evidence_review_bridge(package, args.output_dir) if args.output_dir else package
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
