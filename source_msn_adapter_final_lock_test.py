from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_final_lock import COMPLETE, LOCKED_WITH_LIVE_REVIEW, build_final_lock_report, write_final_lock_report, REQUIRED_CODE_FILES, REQUIRED_DOC_FILES


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_final_lock_report_complete_with_live_result() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        bundle = root / "bundle"
        for name in REQUIRED_CODE_FILES + REQUIRED_DOC_FILES:
            _write(repo / name, "placeholder\n")
        _write(bundle / "article.json", '{"title":"Article", "source_role":"secondary_framing_only"}')
        _write(bundle / "comments.json", '{"comments":[{"text":"x"}]}')
        _write(bundle / "profiles.json", '{"profiles":[{"name":"x"}]}')
        _write(bundle / "local_viewer" / "open_local_viewer.cmd", "echo viewer\n")
        _write(bundle / "rendered-page.html", "<html>rendered page</html>")
        _write(bundle / "archive" / "rendered-page.warc.gz", "warc")
        _write(bundle / "media" / "media_inventory.json", '{"media":[{"kind":"image", "visible_credit":"credit"}]}')
        _write(bundle / "reports" / "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json", '{"status":"CONFIDENT_WITH_MANUAL_REVIEW"}')
        _write(bundle / "reports" / "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json", '{"status":"CONFIDENT_WITH_MANUAL_REVIEW"}')
        _write(bundle / "reports" / "MSN_SOURCE_ADAPTER_LIVE_RECONCILIATION_REPORT.json", '{"status":"CONFIDENT_WITH_MANUAL_REVIEW"}')
        _write(bundle / "02_MSN_LIVE_ACCEPTANCE_RESULT_TEMPLATE.json", json.dumps({"status":"COMPLETE", "passed": True}))
        report = build_final_lock_report(bundle, repo)
        assert report.status == COMPLETE
        json_path, md_path = write_final_lock_report(report, bundle / "reports")
        assert json_path.exists()
        assert md_path.exists()
        assert "COMPLETE" in md_path.read_text(encoding="utf-8")


def test_final_lock_requires_manual_live_for_complete() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        bundle = root / "bundle"
        for name in REQUIRED_CODE_FILES + REQUIRED_DOC_FILES:
            _write(repo / name, "placeholder\n")
        _write(bundle / "article.json", '{"title":"Article", "source_role":"secondary_framing_only"}')
        _write(bundle / "comments.json", "comments")
        _write(bundle / "profiles.json", "profiles")
        _write(bundle / "local_viewer" / "open_local_viewer.cmd", "echo viewer\n")
        _write(bundle / "archive" / "rendered-page.warc.gz", "warc")
        _write(bundle / "media" / "media_inventory.json", "media")
        _write(bundle / "reports" / "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json", "report")
        report = build_final_lock_report(bundle, repo)
        assert report.status == LOCKED_WITH_LIVE_REVIEW
        assert report.live_acceptance_result["positive"] is False


def main() -> int:
    test_final_lock_report_complete_with_live_result()
    test_final_lock_requires_manual_live_for_complete()
    print("MSN final lock self-test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
