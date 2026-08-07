from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from capture_msn_manual_archive_result_intake import build_msn_manual_archive_result_intake
from capture_msn_manual_archive_result_intake_store import store_msn_manual_archive_result_intake
from capture_msn_manual_archive_result_intake_verifier import verify_msn_manual_archive_result_intake


def _fixture_handoff() -> dict[str, object]:
    return {
        "schema_version": "msn_manual_archive_handoff_v1",
        "archive_handoff_status": "MSN_MANUAL_ARCHIVE_HANDOFF_READY",
        "queue_item_id": "msn.queue",
        "release_id": "msn.queue.release.1234",
        "archive_handoff_id": "msn.queue.release.1234.archive_handoff.abc123",
        "source_url": "https://www.msn.com/en-gb/news/example-article/ar-AA123456",
        "source_url_sha256": "sourcehash",
        "readiness_issues": [],
        "archive_tasks": [
            {"task_id": "task.archive_today", "provider": "archive_today"},
            {"task_id": "task.ghostarchive", "provider": "ghostarchive"},
        ],
    }


def _fixture_results() -> list[dict[str, object]]:
    return [
        {"provider": "archive_today", "task_id": "task.archive_today", "result_status": "archived", "archive_url_or_artifact_id": "https://archive.ph/example123", "captured_at_utc": "2026-08-07T17:30:00Z"},
        {"provider": "ghostarchive", "task_id": "task.ghostarchive", "result_status": "skipped", "failure_reason": "not needed"},
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Intake operator-supplied manual archive results for an MSN release handoff.")
    parser.add_argument("--archive-handoff-json", required=True, help="Path to msn_manual_archive_handoff_v1 JSON")
    parser.add_argument("--archive-results-json", required=True, help="Path to operator-supplied archive result JSON")
    parser.add_argument("--output-dir", required=True, help="Directory where intake files will be written")
    parser.add_argument("--operator-label", default="manual_operator")
    parser.add_argument("--intake-notes", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handoff = json.loads(Path(args.archive_handoff_json).read_text(encoding="utf-8"))
    results = json.loads(Path(args.archive_results_json).read_text(encoding="utf-8"))
    intake = build_msn_manual_archive_result_intake(
        handoff,
        results,
        operator_label=args.operator_label,
        intake_notes=args.intake_notes,
    )
    verification = verify_msn_manual_archive_result_intake(intake)
    stored = store_msn_manual_archive_result_intake(intake, args.output_dir)
    output = dict(stored)
    output["verification"] = verification
    print(json.dumps(output, sort_keys=True, indent=2, ensure_ascii=False))
    return 0 if verification["verified"] else 2


def _run_self_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = root / "handoff.json"
        results_path = root / "results.json"
        out_dir = root / "out"
        handoff_path.write_text(json.dumps(_fixture_handoff()), encoding="utf-8")
        results_path.write_text(json.dumps({"results": _fixture_results()}), encoding="utf-8")
        exit_code = main([
            "--archive-handoff-json",
            str(handoff_path),
            "--archive-results-json",
            str(results_path),
            "--output-dir",
            str(out_dir),
            "--operator-label",
            "operator",
        ])
        assert exit_code == 0
        assert len(list(out_dir.glob("*.json"))) == 4
    print("MSN manual archive result intake CLI self-test passed.")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        _run_self_test()
    else:
        raise SystemExit(main())
