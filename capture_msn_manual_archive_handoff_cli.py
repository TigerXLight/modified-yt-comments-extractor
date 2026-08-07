from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from capture_msn_manual_archive_handoff import build_msn_manual_archive_handoff
from capture_msn_manual_archive_handoff_store import store_msn_manual_archive_handoff
from capture_msn_manual_archive_handoff_verifier import verify_msn_manual_archive_handoff


def _fixture_audit() -> dict[str, object]:
    return {
        "schema_version": "msn_manual_release_audit_report_v1",
        "audit_status": "MSN_MANUAL_RELEASE_AUDIT_READY",
        "queue_item_id": "msn.queue",
        "release_id": "msn.queue.release.1234",
        "audit_report_id": "msn.queue.release.1234.audit.abcdef123456",
        "readiness_issues": [],
        "artifact_quality": {"artifact_quality_passed": True},
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a manual-only MSN archive handoff packet from a release audit report.")
    parser.add_argument("--audit-report-json", required=True, help="Path to msn_manual_release_audit_report_v1 JSON")
    parser.add_argument("--source-url", required=True, help="Source URL to archive manually")
    parser.add_argument("--output-dir", required=True, help="Directory where the handoff files will be written")
    parser.add_argument("--provider", action="append", default=None, help="Archive provider; repeat for multiple providers")
    parser.add_argument("--operator-label", default="manual_operator")
    parser.add_argument("--archive-notes", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    audit = json.loads(Path(args.audit_report_json).read_text(encoding="utf-8"))
    handoff = build_msn_manual_archive_handoff(
        audit,
        source_url=args.source_url,
        providers=args.provider,
        operator_label=args.operator_label,
        archive_notes=args.archive_notes,
    )
    verification = verify_msn_manual_archive_handoff(handoff)
    stored = store_msn_manual_archive_handoff(handoff, args.output_dir)
    output = dict(stored)
    output["verification"] = verification
    print(json.dumps(output, sort_keys=True, indent=2, ensure_ascii=False))
    return 0 if verification["verified"] else 2


def _run_self_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        audit_path = root / "audit.json"
        out_dir = root / "out"
        audit_path.write_text(json.dumps(_fixture_audit()), encoding="utf-8")
        exit_code = main([
            "--audit-report-json",
            str(audit_path),
            "--source-url",
            "https://www.msn.com/en-gb/news/example-article/ar-AA123456",
            "--output-dir",
            str(out_dir),
            "--provider",
            "archive_today",
            "--provider",
            "ghostarchive",
            "--operator-label",
            "operator",
        ])
        assert exit_code == 0
        assert len(list(out_dir.glob("*.json"))) == 3
    print("MSN manual archive handoff CLI self-test passed.")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        _run_self_test()
    else:
        raise SystemExit(main())
