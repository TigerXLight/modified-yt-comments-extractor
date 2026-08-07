from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from capture_msn_manual_evidence_queue_item import build_msn_manual_evidence_queue_item, msn_manual_evidence_queue_item_to_json
from capture_msn_manual_evidence_queue_store import store_msn_manual_evidence_queue_item, msn_manual_evidence_queue_store_result_to_json
from capture_msn_manual_evidence_queue_verifier import verify_msn_manual_evidence_queue_item_payload, msn_manual_evidence_queue_verification_report_to_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Queue an implemented MSN manual Total Export pipeline report for Source Evidence review.")
    parser.add_argument("--pipeline-json", required=True, help="Explicit path to a pipeline JSON report or CLI output JSON.")
    parser.add_argument("--output-dir", required=True, help="Directory where queue JSON files will be written.")
    parser.add_argument("--queue-id", default="source_evidence_review_queue")
    parser.add_argument("--file-prefix", default="msn_manual_evidence_queue")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = json.loads(Path(args.pipeline_json).read_text(encoding="utf-8"))
        item = build_msn_manual_evidence_queue_item(payload, queue_id=args.queue_id)
        item_payload = json.loads(msn_manual_evidence_queue_item_to_json(item))
        verifier = verify_msn_manual_evidence_queue_item_payload(item_payload)
        store = store_msn_manual_evidence_queue_item(output_dir=Path(args.output_dir), item=item, file_prefix=args.file_prefix)
        print(
            json.dumps(
                {
                    "evidence_queue_item": item_payload,
                    "evidence_queue_verifier": json.loads(msn_manual_evidence_queue_verification_report_to_json(verifier)),
                    "evidence_queue_store_result": json.loads(msn_manual_evidence_queue_store_result_to_json(store)),
                },
                sort_keys=True,
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0 if verifier.ready_for_evidence_queue_review else 3
    except Exception as exc:  # pragma: no cover - exercised by subprocess test
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
