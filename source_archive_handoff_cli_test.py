from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path

from source_archive_handoff_cli import main
from source_archive_handoff_test import _release_audit_report, _release_archive_handoff, _traceability_map


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")


def test_source_archive_handoff_cli_writes_outputs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report = root / "audit.json"
        traceability = root / "traceability.json"
        prior = root / "prior_handoff.json"
        out = root / "out"
        _write_json(report, _release_audit_report())
        _write_json(traceability, _traceability_map())
        _write_json(prior, _release_archive_handoff())
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = main(
                [
                    "--release-audit-report-json",
                    str(report),
                    "--traceability-map-json",
                    str(traceability),
                    "--release-archive-handoff-json",
                    str(prior),
                    "--archive-provider",
                    "archive_today",
                    "--archive-provider",
                    "ghostarchive",
                    "--operator-id",
                    "fixture_operator",
                    "--output-dir",
                    str(out),
                ]
            )
        assert rc == 0
        receipt = json.loads(stdout.getvalue())
        assert receipt["store_status"] == "STORED"
        assert receipt["verification"]["verified"] is True
        assert receipt["output_file_count"] == 5
        assert any(item["role"] == "source_archive_result_templates" for item in receipt["stored_files"])


if __name__ == "__main__":
    test_source_archive_handoff_cli_writes_outputs()
    print("Source Archive Handoff CLI self-test passed.")
