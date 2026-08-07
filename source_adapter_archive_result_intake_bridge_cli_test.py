from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path

from source_adapter_archive_result_intake_bridge_cli import main
from source_adapter_archive_result_intake_bridge_test import fixture_archive_handoff_bridge, fixture_operator_results


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def main_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        archive_handoff_bridge = fixture_archive_handoff_bridge()
        bridge_json = root / "archive_handoff_bridge.json"
        result_json = root / "operator_archive_results.json"
        out = root / "out"
        _write_json(bridge_json, archive_handoff_bridge)
        _write_json(result_json, fixture_operator_results(archive_handoff_bridge))
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = main(
                [
                    "--archive-handoff-bridge-json",
                    str(bridge_json),
                    "--archive-result-json",
                    str(result_json),
                    "--operator-id",
                    "archive_result_operator_fixture",
                    "--intake-note",
                    "CLI fixture",
                    "--output-dir",
                    str(out),
                ]
            )
        assert rc == 0
        receipt = json.loads(stdout.getvalue())
        assert receipt["schema_version"] == "source_adapter_archive_result_intake_bridge_store_v1"
        assert receipt["store_status"] == "STORED"
        assert receipt["verification"]["verified"] is True
        assert receipt["output_file_count"] == 5
        assert any(item["role"] == "source_adapter_archive_review_batch_handoff" for item in receipt["stored_files"])


if __name__ == "__main__":
    main_test()
    print("Source Adapter Archive Result Intake Bridge CLI self-test passed.")
