from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_runtime_receipt_review_bridge import build_source_adapter_runtime_receipt_review_bridge
from source_adapter_runtime_receipt_review_bridge_store import store_source_adapter_runtime_receipt_review_bridge


def _load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review shared Adapter Runtime Wiring Bridge receipts.")
    parser.add_argument("--runtime-wiring-bridge-json", required=True, help="Adapter Runtime Wiring Bridge package JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for bridge artifacts.")
    parser.add_argument("--reviewer-id", default="operator")
    parser.add_argument("--acceptance-decision", choices=["ACCEPTED", "ACCEPTED_WITH_NOTES"], default="ACCEPTED")
    parser.add_argument("--required-capability", action="append", default=None, help="Required accepted capability; repeat to override the default full catalog.")
    parser.add_argument("--review-note", action="append", default=[], help="Optional runtime receipt review note; may be repeated.")
    args = parser.parse_args(argv)

    wiring = _load_json(args.runtime_wiring_bridge_json)
    package = build_source_adapter_runtime_receipt_review_bridge(
        wiring,
        required_capabilities=args.required_capability,
        acceptance_decision=args.acceptance_decision,
        reviewer_id=args.reviewer_id,
        review_notes=args.review_note,
    )
    result = store_source_adapter_runtime_receipt_review_bridge(package, args.output_dir) if args.output_dir else package
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
