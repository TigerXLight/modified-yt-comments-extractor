from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from source_release_audit import build_source_release_audit, dump_json, load_json_file
from source_release_audit_store import store_source_release_audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a shared source release audit from a release index record.")
    parser.add_argument("--release-index-record-json", required=True, help="Path to source release index record JSON.")
    parser.add_argument("--release-inventory-json", help="Optional path to source release inventory JSON.")
    parser.add_argument("--export-bundle-handoff-json", help="Optional path to source release export-bundle handoff JSON.")
    parser.add_argument("--auditor-id", default="manual_auditor", help="Non-secret auditor/operator identifier.")
    parser.add_argument("--audit-profile", default="source_adapter_shared_release_audit_v1", help="Deterministic release audit profile label.")
    parser.add_argument("--audit-note", action="append", default=[], help="Optional audit note; may be repeated.")
    parser.add_argument("--output-dir", required=True, help="Directory where output JSON files will be written.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    outputs = build_source_release_audit(
        release_index_record=load_json_file(args.release_index_record_json),
        release_inventory=load_json_file(args.release_inventory_json) if args.release_inventory_json else None,
        export_bundle_handoff=load_json_file(args.export_bundle_handoff_json) if args.export_bundle_handoff_json else None,
        auditor_id=args.auditor_id,
        audit_profile=args.audit_profile,
        audit_notes=args.audit_note,
    )
    receipt = store_source_release_audit(outputs.as_dict(), Path(args.output_dir))
    print(dump_json(receipt), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
