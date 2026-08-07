from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from source_adapter_release_audit_bridge_test import fixture_release_index_bridge


def main() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        input_path = root / "release_index_bridge.json"
        output_dir = root / "out"
        input_path.write_text(json.dumps(fixture_release_index_bridge(), indent=2, sort_keys=True), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "source_adapter_release_audit_bridge_cli.py",
                "--release-index-bridge-json",
                str(input_path),
                "--output-dir",
                str(output_dir),
                "--auditor-id",
                "cli_auditor",
                "--audit-note",
                "CLI release audit bridge test.",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
    assert payload["schema_version"] == "source_adapter_release_audit_bridge_store_v1"
    assert payload["store_status"] == "STORED"
    assert payload["release_audit_count"] == 1
    assert payload["verification"]["verified"] is True


if __name__ == "__main__":
    main()
    print("Source Adapter Release Audit Bridge CLI self-test passed.")
