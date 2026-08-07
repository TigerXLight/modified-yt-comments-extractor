from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from capture_msn_manual_release_audit_report import build_msn_manual_release_audit_report
from capture_msn_manual_release_audit_report_store import store_msn_manual_release_audit_report
from capture_msn_manual_release_audit_report_verifier import verify_msn_manual_release_audit_report


def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an MSN manual release audit report from a pipeline closeout JSON.")
    parser.add_argument("--pipeline-closeout-json", required=True)
    parser.add_argument("--store-report-json", action="append", default=[])
    parser.add_argument("--operator-label", default="manual_operator")
    parser.add_argument("--audit-notes", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true", help="Print the store result as JSON.")
    args = parser.parse_args(argv)

    pipeline_closeout = _load_json(args.pipeline_closeout_json)
    store_reports = [_load_json(path) for path in args.store_report_json]
    packet = build_msn_manual_release_audit_report(
        pipeline_closeout,
        store_reports=store_reports,
        operator_label=args.operator_label,
        audit_notes=args.audit_notes,
    )
    verification = verify_msn_manual_release_audit_report(packet)
    result = store_msn_manual_release_audit_report(packet, args.output_dir)
    result["verification"] = verification

    if args.json:
        print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
    else:
        print(f"Stored MSN manual release audit report: {result['audit_report_id']}")
        print(f"Verified: {verification['verified']}")
    return 0 if verification["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
