from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_archive_review_bridge import build_source_adapter_archive_review_bridge
from source_adapter_archive_review_bridge_store import store_source_adapter_archive_review_bridge


def _load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build shared Adapter Archive Review Bridge packages.")
    parser.add_argument("--archive-result-intake-bridge-json", required=True, help="Adapter Archive Result Intake Bridge package JSON.")
    parser.add_argument("--archive-review-decision-json", help="Optional shared or per-intake archive review decision JSON.")
    parser.add_argument("--decision", choices=["APPROVED", "REJECTED", "REVISION_REQUESTED"], help="Shared archive review decision when no decision JSON is supplied.")
    parser.add_argument("--output-dir", help="Optional output directory for bridge artifacts.")
    parser.add_argument("--reviewer-id", default="manual_archive_reviewer", help="Non-secret archive reviewer identifier.")
    parser.add_argument("--review-note", action="append", default=[], help="Optional archive review note; may be repeated.")
    args = parser.parse_args(argv)

    bridge = _load_json(args.archive_result_intake_bridge_json)
    decision: object = _load_json(args.archive_review_decision_json) if args.archive_review_decision_json else {"decision": args.decision or "APPROVED"}
    package = build_source_adapter_archive_review_bridge(
        bridge,
        archive_reviewer_decision=decision,
        reviewer_id=args.reviewer_id,
        review_notes=args.review_note,
    )
    result = store_source_adapter_archive_review_bridge(package, args.output_dir) if args.output_dir else package
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
