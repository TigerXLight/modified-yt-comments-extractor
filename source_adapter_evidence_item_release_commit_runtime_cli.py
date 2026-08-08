from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_adapter_evidence_item_release_commit_runtime import build_default_record, build_record, render_record_text
from source_adapter_evidence_item_release_commit_runtime_store import RuntimeStore
from source_adapter_evidence_item_release_commit_runtime_verifier import verify_record, verify_records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evidence Item Release Commit runtime helper")
    parser.add_argument("--runtime-id", default="evidence_item_release_commit-cli")
    parser.add_argument("--input-ref", action="append", default=[])
    parser.add_argument("--output-ref", action="append", default=[])
    parser.add_argument("--operator-approved", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", type=Path)
    parser.add_argument("--read", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.read:
        records = RuntimeStore(args.read).read_all()
        issues = verify_records(records)
        payload = {"records": [record.to_dict() for record in records], "issue_count": len(issues), "issues": issues}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if issues else 0

    record = build_record(
        args.runtime_id,
        input_refs=args.input_ref or ("source-evidence-roadmap",),
        output_refs=args.output_ref or ("redacted-receipt",),
        operator_approved=args.operator_approved,
        metadata={"runtime_title": "Evidence Item Release Commit"},
    )
    issues = verify_record(record)
    if args.write:
        RuntimeStore(args.write).append(record)
    if args.json:
        print(json.dumps({"record": record.to_dict(), "issue_count": len(issues), "issues": issues}, indent=2, sort_keys=True))
    else:
        print(render_record_text(record))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
