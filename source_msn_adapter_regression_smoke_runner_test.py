from __future__ import annotations

import tempfile
from pathlib import Path

from source_msn_adapter_regression_smoke_runner import build_regression_smoke_report, write_regression_smoke_report


def test_smoke_report_ready_to_execute() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        root.mkdir()
        (root / "source_msn_adapter_manifest_test.py").write_text("print('ok')\n", encoding="utf-8")
        out = Path(tmp) / "out"
        report = build_regression_smoke_report(root, out, execute=False, tests=["source_msn_adapter_manifest_test.py"])
        assert report.status == "READY_TO_EXECUTE"
        assert report.results[0].status == "FOUND_NOT_EXECUTED"
        paths = write_regression_smoke_report(report)
        assert Path(paths["json"]).exists()
        assert Path(paths["markdown"]).exists()
        assert Path(paths["csv"]).exists()


def test_smoke_report_missing_tests_is_partial() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        root.mkdir()
        out = Path(tmp) / "out"
        report = build_regression_smoke_report(root, out, execute=False, tests=["missing_test.py"])
        assert report.status == "PARTIAL_MISSING_TESTS"
        assert report.missing_tests == ["missing_test.py"]


if __name__ == "__main__":
    test_smoke_report_ready_to_execute()
    test_smoke_report_missing_tests_is_partial()
    print("MSN regression smoke runner self-test passed.")
