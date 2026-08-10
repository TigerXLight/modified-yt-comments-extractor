from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_done_gate import (
    OVERALL_CONFIDENT,
    OVERALL_NOT_READY,
    OVERALL_PARTIAL,
    OVERALL_READY,
    STATUS_FAIL,
    run_done_gate,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_binary(path: Path, data: bytes = b"x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _make_complete_fixture(root: Path) -> None:
    _write(
        root / "rendered-page.html",
        "<html><head><title>MSN article</title><meta property='og:image' content='hero.jpg'></head>"
        "<body><h1>Article title</h1><img src='hero.jpg'>"
        + ("Article body paragraph with evidence extraction content. " * 40)
        + "</body></html>",
    )
    _write_binary(root / "rendered-page.warc.gz", b"warc")
    _write_binary(root / "archive.viewable-live-capture.wacz", b"strict")
    _write_binary(root / "archive.replayweb-compatible.wacz", b"compatible")
    _write(root / "local_viewer" / "open_local_viewer.cmd", "@echo off\necho viewer\n")
    _write(
        root / "msn-comments-v35-profile-stats.json",
        json.dumps(
            {
                "items": [
                    {
                        "id": "C0001",
                        "author": "A",
                        "body": "comment",
                        "comment_likes": 3,
                        "comment_dislikes": 1,
                    },
                    {"id": "C0002", "body": "This comment was deleted because it didn't meet our guidelines"},
                ]
            }
        ),
    )
    _write(
        root / "profiles.json",
        json.dumps(
            {
                "profiles": [
                    {
                        "author": "A",
                        "profile_cid": "cid-abc",
                        "canonical_url": "https://www.msn.com/community/profile/cid-abc",
                        "account_comments": 12,
                        "account_likes": 99,
                        "account_followers": 2,
                    }
                ]
            }
        ),
    )
    _write(root / "comments.html", "<html>comments viewer</html>")
    _write(root / "comments.txt", "A · 1 Jan\n\ncomment\n\n👍 3 👎 1")
    _write(
        root / "MSN_MEDIA_INVENTORY.json",
        json.dumps(
            {
                "media": [
                    {
                        "media_observed_on_url": "https://www.msn.com/article",
                        "publisher_page_url": "https://www.msn.com/article",
                        "publisher_name": "MSN",
                        "visible_source_credit": "Google Street View",
                        "claimed_original_source": "The Independent",
                        "source_role": "SECONDARY_FRAMING_ONLY",
                        "primary_source_status": "PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED",
                        "source_chain_gap": True,
                        "status": "REGISTERED",
                    }
                ]
            }
        ),
    )
    _write(root / "MSN_MEDIA_DOWNLOAD_RESULTS.json", json.dumps({"results": [{"status": "DOWNLOADED"}]}))
    _write_binary(root / "media" / "hero.jpg", b"image-bytes")
    _write(
        root / "MSN_SOURCE_ADAPTER_MANIFEST.json",
        json.dumps(
            {
                "source_platform": "MSN",
                "publisher_name": "The Independent",
                "visible_source_credit": "Google Street View",
                "source_role": "SECONDARY_FRAMING_ONLY",
                "primary_source_status": "PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED",
                "source_chain_gap": True,
                "media_observed_on_url": "https://www.msn.com/article",
                "publisher_framing_summary": "MSN republished article from The Independent.",
            }
        ),
    )
    _write(root / "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json", json.dumps({"overall_status": "CONFIDENT_WITH_MANUAL_REVIEW"}))
    _write(root / "MSN_SOURCE_ADAPTER_READINESS.json", json.dumps({"overall_status": "READY"}))
    _write(root / "MSN_SOURCE_ADAPTER_RELEASE_REPORT.json", json.dumps({"overall_status": "READY"}))
    _write(root / "MSN_SOURCE_ADAPTER_TOTAL_PACKAGE.json", json.dumps({"artifacts": []}))
    _write(root / "MSN_ADAPTER_FINAL_VALIDATION_REPORT.md", "# final validation")
    _write(
        root / "MSN_MANUAL_VALIDATION_RESULT.json",
        json.dumps(
            {
                "article_status": "PASS",
                "comments_status": "PASS",
                "archive_status": "PASS",
                "media_status": "PASS",
                "source_chain_status": "PASS",
            }
        ),
    )


def test_done_gate_reports_ready_for_complete_fixture() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_complete_fixture(root)
        report = run_done_gate(root)
        assert report.overall_status in {OVERALL_READY, OVERALL_CONFIDENT}
        assert (root / "reports" / "MSN_ADAPTER_DONE_GATE_REPORT.json").exists()
        assert (root / "reports" / "MSN_ADAPTER_DONE_GATE_REPORT.md").exists()
        statuses = {section.name: section.status for section in report.sections}
        assert statuses["article_extraction"] in {"PASS", "PARTIAL"}
        assert statuses["comments_profile_extraction"] == "PASS"
        assert statuses["media_download_registration"] == "PASS"
        assert statuses["source_role_provenance"] == "PASS"


def test_done_gate_is_not_ready_for_empty_folder() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report = run_done_gate(root)
        assert report.overall_status in {OVERALL_NOT_READY, OVERALL_PARTIAL}
        statuses = {section.name: section.status for section in report.sections}
        assert statuses["article_extraction"] == STATUS_FAIL
        assert statuses["comments_profile_extraction"] == STATUS_FAIL


if __name__ == "__main__":
    test_done_gate_reports_ready_for_complete_fixture()
    test_done_gate_is_not_ready_for_empty_folder()
    print("MSN adapter done-gate self-test passed.")
