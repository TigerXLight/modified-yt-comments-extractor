from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_live_result_reconciler import (
    FINAL_BLOCKED,
    FINAL_COMPLETE,
    FINAL_CONFIDENT_REVIEW,
    FINAL_PARTIAL,
    REPORT_JSON,
    REPORT_MD,
    build_reconciliation_report,
    main,
    write_report,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _base_fixture(root: Path) -> None:
    _write(root / "reports" / "MSN_SOURCE_ADAPTER_OPERATOR_FINAL_SUMMARY.json", json.dumps({
        "final_status": "CONFIDENT_WITH_MANUAL_REVIEW",
        "checks": [
            {"name": "article", "status": "PASS"},
            {"name": "comments", "status": "PASS"},
            {"name": "media", "status": "PASS"},
        ],
        "source_role": "SECONDARY_FRAMING_ONLY",
        "primary_source_status": "PRIMARY_SOURCE_NOT_LOCATED",
        "source_chain_gap": True,
        "msn": "republisher",
        "visible publisher": "The Independent",
        "original source": "not located",
    }))
    _write(root / "reports" / "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json", json.dumps({
        "final_status": "CONFIDENT_WITH_MANUAL_REVIEW",
        "checks": [{"name": "acceptance", "status": "PASS"}],
    }))
    _write(root / "reports" / "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json", json.dumps({
        "final_status": "CONFIDENT_WITH_MANUAL_REVIEW",
        "checks": [{"name": "final_validation", "status": "PASS"}],
    }))
    _write(root / "reports" / "MSN_SOURCE_ADAPTER_DONE_GATE_REPORT.json", json.dumps({
        "final_status": "CONFIDENT_WITH_MANUAL_REVIEW",
        "checks": [{"name": "done_gate", "status": "PASS"}],
    }))
    _write(root / "reports" / "MSN_SOURCE_ADAPTER_COMPLETION_SUMMARY.json", json.dumps({
        "final_status": "CONFIDENT_WITH_MANUAL_REVIEW",
    }))
    _write(root / "article" / "article.json", json.dumps({"title": "Example", "source_role": "SECONDARY_FRAMING_ONLY"}))
    _write(root / "comments" / "comments.json", json.dumps({"comments": [{"id": "c1", "text": "hello"}]}))
    _write(root / "profiles" / "profiles.json", json.dumps({"profiles": [{"cid": "p1", "comments": 1, "likes": 2, "followers": 3}]}))
    _write(root / "local_viewer" / "open_local_viewer.cmd", "@echo off\necho open\n")
    _write(root / "archive" / "rendered-page.html", "<html><body>article</body></html>")
    _write(root / "archive" / "rendered-page.warc.gz", "fake-warc")
    _write(root / "archive" / "archive.viewable-live-capture.wacz", "fake-wacz")
    _write(root / "media" / "MSN_MEDIA_INVENTORY.json", json.dumps({
        "media": [{"url": "https://example.test/image.jpg", "download_status": "PASS", "sha256": "abc", "video_candidate": False}],
        "video": [{"url": "https://example.test/stream.m3u8", "status": "candidate"}],
        "hash": "abc",
        "candidate": True,
        "download": "recorded",
    }))


def test_missing_live_result_is_manual_review() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _base_fixture(root)
        report = build_reconciliation_report(root)
        assert report.final_status == FINAL_CONFIDENT_REVIEW, report.to_dict()
        check = next(c for c in report.checks if c.name == "manual_live_acceptance_result_present")
        assert check.status == "FAIL"
        out = root / "out"
        json_path, md_path = write_report(report, out)
        assert json_path.name == REPORT_JSON
        assert md_path.name == REPORT_MD
        assert json.loads(json_path.read_text(encoding="utf-8"))["final_status"] == FINAL_CONFIDENT_REVIEW
        assert "manual_live_acceptance_result_present" in md_path.read_text(encoding="utf-8")


def test_complete_live_result_marks_complete() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _base_fixture(root)
        _write(root / "manual" / "MSN_LIVE_ACCEPTANCE_RESULT.json", json.dumps({
            "final_status": "PASS",
            "article": "PASS",
            "comments": "PASS",
            "profile": "PASS",
            "offline": "PASS",
            "warc": "PASS",
            "media": "PASS",
            "source": "PASS",
            "notes": "Article comments profile offline warc media source all passed.",
        }))
        report = build_reconciliation_report(root)
        assert report.final_status == FINAL_COMPLETE, report.to_dict()


def test_failed_static_report_blocks_completion() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _base_fixture(root)
        _write(root / "manual" / "MSN_LIVE_ACCEPTANCE_RESULT.json", json.dumps({
            "final_status": "PASS",
            "article": "PASS comments profile offline warc media source",
        }))
        _write(root / "reports" / "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json", json.dumps({
            "final_status": "FAIL",
            "checks": [{"name": "comments", "status": "FAIL"}],
        }))
        report = build_reconciliation_report(root)
        assert report.final_status == FINAL_BLOCKED, report.to_dict()


def test_cli_writes_outputs() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _base_fixture(root)
        out = root / "cli_out"
        rc = main(["--root", str(root), "--out", str(out)])
        assert rc == 0
        assert (out / REPORT_JSON).exists()
        assert (out / REPORT_MD).exists()


if __name__ == "__main__":
    test_missing_live_result_is_manual_review()
    test_complete_live_result_marks_complete()
    test_failed_static_report_blocks_completion()
    test_cli_writes_outputs()
    print("MSN live result reconciler self-test passed.")
