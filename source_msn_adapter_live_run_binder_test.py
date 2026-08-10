from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_live_run_binder import build_live_run_binder


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_pending_without_live_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "msn"
        out = Path(tmp) / "binder"
        _write(root / "rendered-page.html", "<html>article</html>")
        _write(root / "comments.json", "[]")
        report = build_live_run_binder(root, out)
        assert report.status == "BINDER_PENDING_LIVE_EVIDENCE"
        assert (out / "MSN_SOURCE_ADAPTER_LIVE_RUN_BINDER.json").exists()
        assert (out / "MSN_SOURCE_ADAPTER_LIVE_RUN_BINDER.md").exists()
        assert (out / "MSN_SOURCE_ADAPTER_LIVE_RUN_BINDER_FILES.csv").exists()


def test_complete_with_positive_live_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "msn"
        out = Path(tmp) / "binder"
        checks = {
            "article_extraction": "pass",
            "comments_extraction": "pass",
            "profile_export": "pass",
            "offline_viewer": "pass",
            "warc_or_archive": "pass",
            "media_discovery": "pass",
            "source_chain_preserved": "pass",
        }
        _write(root / "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_RESULT.json", json.dumps({"checks": checks}))
        _write(root / "rendered-page.html", "<html>article</html>")
        _write(root / "article.warc.gz", "warc")
        _write(root / "comments.json", "[]")
        _write(root / "profiles.csv", "profile\n")
        _write(root / "media_inventory.json", "[]")
        _write(root / "MSN_SOURCE_CHAIN_EVIDENCE.json", "{}")
        report = build_live_run_binder(root, out)
        assert report.status == "BINDER_COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"
        data = json.loads((out / "MSN_SOURCE_ADAPTER_LIVE_RUN_BINDER.json").read_text(encoding="utf-8"))
        assert data["live_evidence"]["positive"] is True


def test_blocked_with_missing_check() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "msn"
        out = Path(tmp) / "binder"
        _write(root / "MSN_LIVE_ACCEPTANCE_RESULT.json", json.dumps({"checks": {"article_extraction": "pass"}}))
        report = build_live_run_binder(root, out)
        assert report.status == "BINDER_BLOCKED"
        assert "comments_extraction" in report.live_evidence.missing_checks


if __name__ == "__main__":
    test_pending_without_live_evidence()
    test_complete_with_positive_live_evidence()
    test_blocked_with_missing_check()
    print("MSN live run binder self-test passed.")
