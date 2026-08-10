from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_closeout_orchestrator import run_closeout
from source_msn_adapter_goal_matrix import COMPLETE, CONFIDENT_WITH_MANUAL_REVIEW


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_static_confident_fixture(root: Path) -> None:
    write(root / "article" / "rendered-page.html", "<html><article>MSN article body from The Independent. source_role primary_source_status original source gap media credit Google Street View publisher MSN</article></html>")
    write(root / "comments" / "msn-comments-v35-profile-stats.md", "# Comments\nPASS\nNested replies and deleted placeholders preserved.")
    write(root / "profiles" / "msn-comments-v35-profile-stats-profiles.csv", "display_name,profile_url,comments,likes,followers\nUser,https://www.msn.com/profile/abc,10,20,3\n")
    write(root / "archive" / "open_local_viewer.cmd", "@echo off\necho viewer PASS\n")
    write(root / "archive" / "rendered-page.warc.gz", "fake warc bytes")
    write(root / "archive" / "archive.viewable-live-capture.wacz", "fake wacz bytes")
    write(root / "media" / "MSN_MEDIA_INVENTORY.json", json.dumps({
        "status": "PASS",
        "items": [{
            "url": "https://example.invalid/hero.jpg",
            "download_status": "PASS",
            "sha256": "abc",
            "source_role": "SECONDARY_FRAMING_ONLY",
            "primary_source_status": "PRIMARY_SOURCE_NOT_LOCATED",
            "captured_platform": "MSN",
            "visible_publisher": "The Independent",
            "visible_media_credit": "Google Street View",
            "original_source_gap": True,
            "video_candidate_status": "NOT_APPLICABLE"
        }]
    }, indent=2))
    write(root / "reports" / "MSN_SOURCE_ADAPTER_READINESS_REPORT.json", json.dumps({"status": "PASS", "source_role": "ok", "primary_source_status": "ok"}))
    write(root / "reports" / "MSN_SOURCE_ADAPTER_RELEASE_REPORT.json", json.dumps({"status": "PASS"}))
    write(root / "reports" / "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json", json.dumps({"final_status": "CONFIDENT_WITH_MANUAL_REVIEW"}))
    write(root / "reports" / "MSN_SOURCE_ADAPTER_DONE_GATE_REPORT.json", json.dumps({"status": "PASS"}))
    write(root / "reports" / "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json", json.dumps({"final_status": "CONFIDENT_WITH_MANUAL_REVIEW"}))
    write(root / "reports" / "MSN_SOURCE_ADAPTER_OPERATOR_FINAL_SUMMARY.json", json.dumps({"final_status": "CONFIDENT_WITH_MANUAL_REVIEW"}))
    write(root / "reports" / "MSN_SOURCE_ADAPTER_LIVE_RECONCILIATION_REPORT.json", json.dumps({"final_status": "CONFIDENT_WITH_MANUAL_REVIEW"}))


def test_closeout_confident_without_manual_live_result() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "msn_output"
        make_static_confident_fixture(root)
        report, written = run_closeout(root, root / "closeout")
        assert report.final_status == CONFIDENT_WITH_MANUAL_REVIEW
        assert report.static_status == "PASS"
        assert "manual_live_result" in report.missing_live
        assert Path(written["json"]).exists()
        assert Path(written["markdown"]).exists()
        assert Path(written["csv"]).exists()
        assert Path(written["actions"]).exists()


def test_closeout_complete_with_manual_live_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "msn_output"
        make_static_confident_fixture(root)
        write(root / "02_MSN_LIVE_ACCEPTANCE_RESULT_TEMPLATE.json", json.dumps({
            "status": "PASS",
            "live_article_passed": True,
            "article_extraction_passed": True,
            "comments_export_passed": True,
            "offline_viewer_passed": True,
            "media_review_passed": True,
            "source_chain_review_passed": True
        }, indent=2))
        report, written = run_closeout(root, root / "closeout")
        assert report.final_status == COMPLETE
        assert report.live_status == "PASS"
        loaded = json.loads(Path(written["json"]).read_text(encoding="utf-8"))
        assert loaded["final_status"] == COMPLETE


def test_closeout_detects_missing_folder_as_blocked_or_partial() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "empty"
        root.mkdir()
        report, _ = run_closeout(root, root / "closeout")
        assert report.final_status in {"BLOCKED", "PARTIAL", "INSUFFICIENT_EVIDENCE"}
        assert report.missing_static


if __name__ == "__main__":
    test_closeout_confident_without_manual_live_result()
    test_closeout_complete_with_manual_live_pass()
    test_closeout_detects_missing_folder_as_blocked_or_partial()
    print("MSN closeout orchestrator self-test passed.")
