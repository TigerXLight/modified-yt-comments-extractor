from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from source_msn_adapter_final_selftest_orchestrator import (
    FAIL_STATE,
    PASS_STATE,
    build_report,
    discover_tests,
    write_report,
)


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root / "source_msn_adapter_alpha_test.py", "print('alpha pass')\n")
        _write(root / "source_msn_adapter_beta_test.py", "raise SystemExit(0)\n")
        tests = discover_tests(root, ["source_msn_adapter_*_test.py"])
        assert [p.name for p in tests] == ["source_msn_adapter_alpha_test.py", "source_msn_adapter_beta_test.py"]
        report = build_report(root, ["source_msn_adapter_*_test.py"], python_executable=sys.executable)
        assert report.state == PASS_STATE, report
        assert report.total == 2
        assert report.failed == 0
        out = root / "out_pass"
        paths = write_report(report, out)
        assert Path(paths["json"]).exists()
        loaded = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
        assert loaded["state"] == PASS_STATE

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root / "source_msn_adapter_ok_test.py", "raise SystemExit(0)\n")
        _write(root / "source_msn_adapter_fail_test.py", "print('about to fail')\nraise AssertionError('intentional failure')\n")
        report = build_report(root, ["source_msn_adapter_*_test.py"], python_executable=sys.executable)
        assert report.state == FAIL_STATE, report
        assert report.failed == 1
        assert any("intentional failure" in (r.stderr_tail + r.stdout_tail) for r in report.tests)
        out = root / "out_fail"
        paths = write_report(report, out)
        md = Path(paths["markdown"]).read_text(encoding="utf-8")
        assert "SELFTEST_FAILURES_DETECTED" in md
        assert "intentional failure" in md

    print("MSN final self-test orchestrator self-test passed.")


if __name__ == "__main__":
    main()
