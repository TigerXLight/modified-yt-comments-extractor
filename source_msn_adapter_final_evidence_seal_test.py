from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_final_evidence_seal import build_final_evidence_seal


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8")
    else:
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def test_missing_manual_evidence_is_not_called_complete() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(root / "reports" / "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json", {"final_status": "CONFIDENT_WITH_MANUAL_REVIEW"})
        _write(root / "reports" / "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json", {"overall_status": "CONFIDENT_WITH_MANUAL_REVIEW"})
        _write(root / "article" / "article.json", {"headline": "Example", "source_url": "https://www.msn.com/example"})
        _write(root / "comments" / "comments.json", {"comments": [{"source_comment_id": "c1", "profile_url": "https://example/profile"}]})
        _write(root / "local_viewer" / "open_local_viewer.cmd", "@echo off\n")
        _write(root / "archive" / "capture.warc.gz", "warc placeholder")
        _write(root / "media" / "media_inventory.json", {"media_candidates": [{"image": "hero.jpg", "sha256": "0" * 64}]})
        _write(root / "provenance" / "source_chain.json", {"republisher": "MSN", "visible publisher": "The Independent", "original source": "not located", "primary_source_status": "PRIMARY_SOURCE_NOT_LOCATED"})
        seal = build_final_evidence_seal(root, root / "seal")
        assert seal.final_status == "CONFIDENT_WITH_MANUAL_REVIEW"
        assert seal.manual_live_evidence_status == "MISSING"
        assert any("manual/live" in reason.lower() for reason in seal.blocking_reasons)
        assert Path(seal.outputs["json"]).exists()
        assert Path(seal.outputs["markdown"]).exists()
        assert Path(seal.outputs["csv"]).exists()


def test_positive_manual_evidence_can_complete() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(root / "reports" / "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json", {"final_status": "PASS"})
        _write(root / "reports" / "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json", {"overall_status": "PASS"})
        _write(root / "reports" / "MSN_SOURCE_ADAPTER_DONE_GATE_REPORT.json", {"status": "PASS"})
        _write(root / "manual" / "MSN_LIVE_ACCEPTANCE_RESULT.json", {"overall_status": "PASS", "operator": "manual", "article": "PASS", "comments": "PASS", "media": "PASS"})
        _write(root / "article" / "article.json", {"headline": "Example", "source_url": "https://www.msn.com/example"})
        _write(root / "comments" / "comments.json", {"comments": [{"source_comment_id": "c1", "profile_url": "https://example/profile", "followers": 1}]})
        _write(root / "local_viewer" / "open_local_viewer.cmd", "@echo off\n")
        _write(root / "archive" / "capture.warc.gz", "warc placeholder")
        _write(root / "media" / "media_inventory.json", {"media_candidates": [{"image": "hero.jpg", "download": "PASS", "sha256": "0" * 64}], "video": "not_applicable"})
        _write(root / "package" / "manifest.json", {"total package": True, "bundle": "ok"})
        _write(root / "provenance" / "source_chain.json", {"source_role": "SECONDARY_FRAMING_ONLY", "republisher": "MSN", "visible publisher": "The Independent", "original source": "not located", "primary_source_status": "PRIMARY_SOURCE_NOT_LOCATED"})
        seal = build_final_evidence_seal(root, root / "seal")
        assert seal.final_status == "COMPLETE_WITH_MANUAL_EVIDENCE"
        assert seal.manual_live_evidence_status == "POSITIVE"


def run_self_test() -> None:
    test_missing_manual_evidence_is_not_called_complete()
    test_positive_manual_evidence_can_complete()
    print("MSN final evidence seal self-test passed.")


if __name__ == "__main__":
    run_self_test()
