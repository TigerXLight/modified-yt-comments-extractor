from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from source_archive_handoff import build_source_archive_handoff, dump_json, load_json_file
from source_archive_handoff_store import store_source_archive_handoff


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a shared manual archive handoff from a release audit report.")
    parser.add_argument("--release-audit-report-json", required=True, help="Path to source release audit report JSON.")
    parser.add_argument("--traceability-map-json", help="Optional path to source release traceability map JSON.")
    parser.add_argument("--release-archive-handoff-json", help="Optional path to source release archive handoff JSON from release audit.")
    parser.add_argument("--archive-provider", action="append", default=[], help="Archive provider id; may be repeated. Defaults to common manual providers.")
    parser.add_argument("--operator-id", default="manual_archive_operator", help="Non-secret archive operator identifier.")
    parser.add_argument("--handoff-note", action="append", default=[], help="Optional handoff note; may be repeated.")
    parser.add_argument("--output-dir", required=True, help="Directory where output JSON files will be written.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    outputs = build_source_archive_handoff(
        release_audit_report=load_json_file(args.release_audit_report_json),
        traceability_map=load_json_file(args.traceability_map_json) if args.traceability_map_json else None,
        release_archive_handoff=load_json_file(args.release_archive_handoff_json) if args.release_archive_handoff_json else None,
        archive_providers=args.archive_provider or None,
        operator_id=args.operator_id,
        handoff_notes=args.handoff_note,
    )
    receipt = store_source_archive_handoff(outputs.as_dict(), Path(args.output_dir))
    print(dump_json(receipt), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
