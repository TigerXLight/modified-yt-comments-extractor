from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path

from source_adapter_archive_review_bridge_cli import main
from source_adapter_archive_review_bridge_test import fixture_archive_result_intake_bridge


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def main_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        archive_result_intake_bridge = fixture_archive_result_intake_bridge()
        bridge_json = root / "archive_result_intake_bridge.json"
        decision_json = root / "archive_review_decision.json"
        out = root / "out"
        _write_json(bridge_json, archive_result_intake_bridge)
        _write_json(decision_json, {"decision": "APPROVED", "review_notes": ["CLI decision fixture"]})
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = main(
                [
                    "--archive-result-intake-bridge-json",
                    str(bridge_json),
                    "--archive-review-decision-json",
                    str(decision_json),
                    "--reviewer-id",
                    "archive_reviewer_cli_fixture",
                    "--review-note",
                    "CLI fixture",
                    "--output-dir",
                    str(out),
                ]
            )
        assert rc == 0
        receipt = json.loads(stdout.getvalue())
        assert receipt["schema_version"] == "source_adapter_archive_review_bridge_store_v1"
        assert receipt["store_status"] == "STORED"
        assert receipt["verification"]["verified"] is True
        assert receipt["output_file_count"] == 5
        assert any(item["role"] == "source_adapter_pipeline_closeout_batch_handoff" for item in receipt["stored_files"])


if __name__ == "__main__":
    main_test()
    print("Source Adapter Archive Review Bridge CLI self-test passed.")
