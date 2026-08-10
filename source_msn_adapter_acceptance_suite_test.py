from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_acceptance_suite import (
    AcceptanceStatus,
    CheckStatus,
    build_acceptance_report,
    main,
    write_acceptance_report,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_confident_fixture(root: Path) -> None:
    _write(root / "rendered-page.html", "<html><head><meta property='og:url' content='https://www.msn.com/example'></head><body>MSN article " + ("body " * 180) + " https://www.msn.com/example</body></html>")
    _write(root / "local_viewer" / "open_local_viewer.cmd", "@echo off\necho viewer\n")
    _write(root / "capture-manifest.json", json.dumps({
        "source_url": "https://www.msn.com/example",
        "strict_wacz_status": "experimental_possibly_unsupported",
        "primary_source_status": "PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED",
        "source_role": "SECONDARY_FRAMING_ONLY",
        "source_chain_gap": True,
        "publisher_name": "The Independent",
        "visible_source_credit": "Google Street View",
    }))
    _write(root / "validation.json", json.dumps({"wacz_status": "strict WACZ experimental possibly unsupported"}))
    _write(root / "rendered-page.warc.gz", "fake warc fallback")
    _write(root / "archive.viewable-live-capture.wacz", "fake strict wacz")
    _write(root / "msn-comments-v35-profile-stats.json", json.dumps({"comments": [{"author": "A"}], "profiles": [{"profile_cid": "cid-a"}]}))
    _write(root / "profiles.json", json.dumps([{"author": "A", "account_comments": 2}]))
    _write(root / "media_inventory.json", json.dumps({
        "media": [{
            "media_url": "https://img-s-msn-com.akamaized.net/example.jpg",
            "kind": "image",
            "status": "downloaded",
            "sha256": "a" * 64,
            "publisher_name": "MSN",
            "claimed_original_source": "The Independent",
        }, {
            "media_url": "https://video.example/stream.m3u8",
            "kind": "video",
            "status": "stream_external",
            "poster": "https://example/poster.jpg",
        }]
    }))
    _write(root / "media" / "example.jpg", "not a real image but enough for inventory presence")
    for name in (
        "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json",
        "MSN_SOURCE_ADAPTER_READINESS_REPORT.json",
        "MSN_SOURCE_ADAPTER_RELEASE_REPORT.json",
        "MSN_SOURCE_ADAPTER_DONE_GATE_REPORT.json",
    ):
        _write(root / "reports" / name, json.dumps({"source_role": "SECONDARY_FRAMING_ONLY", "primary_source_status": "PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED", "source_chain_gap": True}))


def test_acceptance_report_confident_fixture() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _make_confident_fixture(root)
        report = build_acceptance_report(root)
        assert report.acceptance_status in {AcceptanceStatus.ACCEPTED, AcceptanceStatus.CONFIDENT_WITH_MANUAL_REVIEW}
        statuses = {check.check_id: check.status for check in report.checks}
        assert statuses["article_extraction"] == CheckStatus.PASS
        assert statuses["comments_profiles"] == CheckStatus.PASS
        assert statuses["offline_viewer"] == CheckStatus.PASS
        assert statuses["archive_replay"] == CheckStatus.PARTIAL
        assert statuses["media_registration"] == CheckStatus.PASS
        assert statuses["video_status"] == CheckStatus.PASS
        assert statuses["source_provenance"] == CheckStatus.PASS


def test_acceptance_report_blocks_missing_required_areas() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "rendered-page.html", "tiny")
        report = build_acceptance_report(root)
        assert report.acceptance_status == AcceptanceStatus.BLOCKED
        assert "comments_profiles" in report.required_failures
        assert "media_registration" in report.required_failures


def test_acceptance_report_writes_json_markdown_csv() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _make_confident_fixture(root)
        out = root / "acceptance"
        report = build_acceptance_report(root)
        json_path, md_path, csv_path = write_acceptance_report(report, out)
        assert json_path.exists()
        assert md_path.exists()
        assert csv_path.exists()
        assert "MSN Source Adapter Acceptance Report" in md_path.read_text(encoding="utf-8")
        loaded = json.loads(json_path.read_text(encoding="utf-8"))
        assert loaded["adapter_name"] == "msn_source_adapter"


def test_acceptance_cli_returns_success_for_confident_fixture() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _make_confident_fixture(root)
        assert main(["--root", str(root), "--output", str(root / "reports")]) == 0
        assert (root / "reports" / "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.md").exists()


if __name__ == "__main__":
    test_acceptance_report_confident_fixture()
    test_acceptance_report_blocks_missing_required_areas()
    test_acceptance_report_writes_json_markdown_csv()
    test_acceptance_cli_returns_success_for_confident_fixture()
    print("MSN acceptance suite self-test passed.")
