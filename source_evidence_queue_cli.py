from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from source_evidence_queue import build_source_evidence_queue, dump_json, load_json_file
from source_evidence_queue_store import store_source_evidence_queue


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a shared source Evidence Queue item from an explicit Total Export package JSON.")
    parser.add_argument("--total-export-package-json", required=True, help="Path to source Total Export package JSON.")
    parser.add_argument("--evidence-queue-handoff-json", help="Optional path to source Total Export Evidence Queue handoff JSON.")
    parser.add_argument("--queue-profile", default="source_adapter_shared_v1", help="Deterministic queue profile label.")
    parser.add_argument("--queue-note", action="append", default=[], help="Optional queue note; may be repeated.")
    parser.add_argument("--output-dir", required=True, help="Directory where output JSON files will be written.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    package = load_json_file(args.total_export_package_json)
    handoff = load_json_file(args.evidence_queue_handoff_json) if args.evidence_queue_handoff_json else None
    outputs = build_source_evidence_queue(
        total_export_package=package,
        evidence_queue_handoff=handoff,
        queue_profile=args.queue_profile,
        queue_notes=args.queue_note,
    )
    receipt = store_source_evidence_queue(outputs.as_dict(), Path(args.output_dir))
    print(dump_json(receipt), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
