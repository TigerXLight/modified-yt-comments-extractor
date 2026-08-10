from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_post_certification_audit import REQUIRED_ARTIFACTS, REQUIRED_DOCS, build_audit, write_audit


def test_post_certification_audit_detects_complete_synthetic_repo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        out = Path(tmp) / "out"
        repo.mkdir()
        for name in REQUIRED_ARTIFACTS:
            (repo / name).write_text("# synthetic\n", encoding="utf-8")
            if name.endswith(".py") and name != "source_msn_adapter_operator_quickstart.py":
                (repo / name.replace(".py", "_test.py")).write_text("# synthetic test\n", encoding="utf-8")
        for name in REQUIRED_DOCS:
            (repo / name).write_text("# synthetic doc\n", encoding="utf-8")
        audit = build_audit(repo)
        assert audit.status == "PASS"
        paths = write_audit(audit, out)
        data = json.loads(paths["json"].read_text(encoding="utf-8"))
        assert data["present_count"] == data["expected_count"]
        assert paths["csv"].is_file()


def test_post_certification_audit_reports_missing_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        audit = build_audit(repo)
        assert audit.status == "FAIL"
        assert audit.present_count == 0


if __name__ == "__main__":
    test_post_certification_audit_detects_complete_synthetic_repo()
    test_post_certification_audit_reports_missing_files()
    print("MSN post-certification audit self-test passed.")
