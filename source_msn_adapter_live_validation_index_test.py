from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_live_validation_index import (
    STATUS_COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE,
    STATUS_READY_FOR_LIVE_EVIDENCE,
    build_live_validation_index,
    write_live_validation_index,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_ready_without_live_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root / "article" / "article.html", "<article>ok</article>")
        _write(root / "comments" / "comments.json", "[]")
        _write(root / "profiles" / "profiles.json", "[]")
        _write(root / "local_viewer" / "open_local_viewer.cmd", "echo viewer")
        _write(root / "archive" / "rendered-page.warc.gz", "warc")
        _write(root / "media" / "MSN_MEDIA_INVENTORY.json", "[]")
        _write(root / "reports" / "MSN_SOURCE_CHAIN_PROVENANCE.json", "{}")
        _write(root / "reports" / "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json", "{}")
        report = build_live_validation_index(root)
        assert report.status == STATUS_READY_FOR_LIVE_EVIDENCE
        assert report.positive_live_evidence is False
        paths = write_live_validation_index(report)
        assert Path(paths["json"]).exists()
        assert Path(paths["markdown"]).exists()
        assert Path(paths["csv"]).exists()


def test_complete_with_positive_live_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for rel, content in {
            "article/article.html": "article",
            "comments/comments.json": "[]",
            "profiles/profiles.json": "[]",
            "local_viewer/rendered-page.html": "html",
            "archive/capture.warc.gz": "warc",
            "media/MSN_MEDIA_RESULTS.json": "[]",
            "reports/MSN_SOURCE_CHAIN_PROVENANCE.json": "{}",
            "reports/MSN_SOURCE_ADAPTER_CERTIFICATION_BUNDLE.json": "{}",
        }.items():
            _write(root / rel, content)
        live = {
            "overall_status": "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE",
            "article_extracted": True,
            "comments_exported": True,
            "profiles_exported": True,
            "offline_viewer_verified": True,
            "archive_verified": True,
            "media_reviewed": True,
            "source_chain_reviewed": True,
        }
        _write(root / "manual" / "MSN_LIVE_EVIDENCE_RESULT.json", json.dumps(live))
        report = build_live_validation_index(root)
        assert report.status == STATUS_COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE
        assert report.positive_live_evidence is True


if __name__ == "__main__":
    test_ready_without_live_evidence()
    test_complete_with_positive_live_evidence()
    print("MSN live validation index self-test passed.")
