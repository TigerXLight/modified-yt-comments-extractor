from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path

from source_adapter_archive_handoff_bridge_cli import main
from source_adapter_archive_handoff_bridge_test import fixture_release_audit_bridge


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def main_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        release_audit_bridge = root / "release_audit_bridge.json"
        out = root / "out"
        _write_json(release_audit_bridge, fixture_release_audit_bridge())
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = main(
                [
                    "--release-audit-bridge-json",
                    str(release_audit_bridge),
                    "--archive-provider",
                    "archive_today",
                    "--archive-provider",
                    "ghostarchive",
                    "--operator-id",
                    "archive_operator_fixture",
                    "--handoff-note",
                    "CLI fixture",
                    "--output-dir",
                    str(out),
                ]
            )
        assert rc == 0
        receipt = json.loads(stdout.getvalue())
        assert receipt["schema_version"] == "source_adapter_archive_handoff_bridge_store_v1"
        assert receipt["store_status"] == "STORED"
        assert receipt["verification"]["verified"] is True
        assert receipt["output_file_count"] == 5
        assert any(item["role"] == "source_adapter_archive_result_intake_batch_handoff" for item in receipt["stored_files"])


if __name__ == "__main__":
    main_test()
    print("Source Adapter Archive Handoff Bridge CLI self-test passed.")
