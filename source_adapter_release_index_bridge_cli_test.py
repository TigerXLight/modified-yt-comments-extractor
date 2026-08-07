from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from source_adapter_release_index_bridge_cli import main
from source_adapter_release_index_bridge_test import fixture_approved_release_bridge


def test_source_adapter_release_index_bridge_cli_writes_outputs() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        bridge_json = root / "approved_release_bridge.json"
        out = root / "out"
        bridge_json.write_text(json.dumps(fixture_approved_release_bridge(), sort_keys=True), encoding="utf-8")
        rc = main([
            "--approved-release-bridge-json", str(bridge_json),
            "--indexer-id", "release_index_operator",
            "--release-note", "Ready for release audit.",
            "--output-dir", str(out),
        ])
        assert rc == 0
        assert len(list(out.glob("*.json"))) == 5


if __name__ == "__main__":
    test_source_adapter_release_index_bridge_cli_writes_outputs()
    print("Source Adapter Release Index Bridge CLI self-test passed.")
