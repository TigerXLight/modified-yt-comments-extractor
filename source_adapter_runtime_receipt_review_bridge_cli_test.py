from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from source_adapter_runtime_receipt_review_bridge_cli import main
from source_adapter_runtime_receipt_review_bridge_test import fixture_runtime_wiring_bridge


def test_runtime_receipt_review_bridge_cli() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        wiring_path = root / "runtime_wiring.json"
        wiring_path.write_text(json.dumps(fixture_runtime_wiring_bridge(), indent=2, sort_keys=True), encoding="utf-8")
        out = root / "out"
        rc = main([
            "--runtime-wiring-bridge-json",
            str(wiring_path),
            "--output-dir",
            str(out),
            "--reviewer-id",
            "operator.fixture",
            "--review-note",
            "cli fixture review",
        ])
        assert rc == 0
        assert len(list(out.glob("*.json"))) == 5


if __name__ == "__main__":
    test_runtime_receipt_review_bridge_cli()
    print("Source Adapter Runtime Receipt Review Bridge CLI self-test passed.")
