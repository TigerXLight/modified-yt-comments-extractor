from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from capture_msn_manual_archive_review_package import build_msn_manual_archive_review_package
from capture_msn_manual_archive_review_package_store import store_msn_manual_archive_review_package
from capture_msn_manual_archive_review_package_verifier import verify_msn_manual_archive_review_package


def _fixture_intake() -> dict[str, object]:
    return {
        "schema_version": "msn_manual_archive_result_intake_v1",
        "archive_result_status": "MSN_MANUAL_ARCHIVE_RESULTS_READY",
        "queue_item_id": "msn.queue",
        "release_id": "msn.queue.release.1234",
        "archive_handoff_id": "msn.queue.release.1234.archive_handoff.abc123",
        "archive_result_intake_id": "msn.queue.release.1234.archive_result_intake.12c8f583eabe",
        "source_url": "https://www.msn.com/en-gb/news/example-article/ar-AA123456",
        "source_url_sha256": "sourcehash",
        "readiness_issues": [],
        "archive_result_summary": {"task_count": 2, "result_count": 2, "successful_result_count": 1},
        "archive_result_queue_update": {"ready_for_post_archive_review": True},
        "archive_result_receipts": [
            {
                "receipt_id": "task.archive_today.archive_result.1234",
                "task_id": "task.archive_today",
                "provider": "archive_today",
                "result_status": "ARCHIVED",
                "archive_url_or_artifact_id": "https://archive.ph/example123",
                "archive_url_or_artifact_sha256": "a" * 64,
                "matched_handoff_task": True,
                "external_call_performed_by_code": False,
            },
            {
                "receipt_id": "task.ghostarchive.archive_result.5678",
                "task_id": "task.ghostarchive",
                "provider": "ghostarchive",
                "result_status": "SKIPPED",
                "archive_url_or_artifact_id": "",
                "archive_url_or_artifact_sha256": "",
                "matched_handoff_task": True,
                "external_call_performed_by_code": False,
            },
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build an MSN manual archive review package from archive result intake JSON.")
    parser.add_argument("--archive-result-intake-json", required=True, help="Path to msn_manual_archive_result_intake_v1 JSON")
    parser.add_argument("--output-dir", required=True, help="Directory where review package files will be written")
    parser.add_argument("--reviewer-label", default="manual_reviewer")
    parser.add_argument("--review-notes", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    intake = json.loads(Path(args.archive_result_intake_json).read_text(encoding="utf-8"))
    package = build_msn_manual_archive_review_package(
        intake,
        reviewer_label=args.reviewer_label,
        review_notes=args.review_notes,
    )
    verification = verify_msn_manual_archive_review_package(package)
    stored = store_msn_manual_archive_review_package(package, args.output_dir)
    output = dict(stored)
    output["verification"] = verification
    print(json.dumps(output, sort_keys=True, indent=2, ensure_ascii=False))
    return 0 if verification["verified"] else 2


def _run_self_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        intake_path = root / "archive_result_intake.json"
        out_dir = root / "out"
        intake_path.write_text(json.dumps(_fixture_intake()), encoding="utf-8")
        exit_code = main([
            "--archive-result-intake-json",
            str(intake_path),
            "--output-dir",
            str(out_dir),
            "--reviewer-label",
            "reviewer",
        ])
        assert exit_code == 0
        assert len(list(out_dir.glob("*.json"))) == 4
    print("MSN manual archive review package CLI self-test passed.")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        _run_self_test()
    else:
        raise SystemExit(main())
