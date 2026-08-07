from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from source_approved_release import build_source_approved_release, dump_json, load_json_file
from source_approved_release_store import store_source_approved_release


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a shared source approved-release package from an approved Evidence Review decision.")
    parser.add_argument("--evidence-review-package-json", required=True, help="Path to source Evidence Review package JSON.")
    parser.add_argument("--evidence-review-decision-json", required=True, help="Path to approved source Evidence Review decision JSON.")
    parser.add_argument("--release-handoff-json", help="Optional path to source Evidence Review release handoff JSON.")
    parser.add_argument("--releaser-id", default="manual_releaser", help="Non-secret releaser/operator identifier.")
    parser.add_argument("--release-profile", default="source_adapter_shared_approved_release_v1", help="Deterministic release profile label.")
    parser.add_argument("--release-note", action="append", default=[], help="Optional release note; may be repeated.")
    parser.add_argument("--output-dir", required=True, help="Directory where output JSON files will be written.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    outputs = build_source_approved_release(
        evidence_review_package=load_json_file(args.evidence_review_package_json),
        evidence_review_decision=load_json_file(args.evidence_review_decision_json),
        release_handoff=load_json_file(args.release_handoff_json) if args.release_handoff_json else None,
        releaser_id=args.releaser_id,
        release_profile=args.release_profile,
        release_notes=args.release_note,
    )
    receipt = store_source_approved_release(outputs.as_dict(), Path(args.output_dir))
    print(dump_json(receipt), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
