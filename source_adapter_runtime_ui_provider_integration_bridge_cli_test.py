from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from source_adapter_runtime_ui_provider_integration_bridge_cli import main
from source_adapter_runtime_ui_provider_integration_bridge_test import fixture_runtime_receipt_review_bridge


def test_runtime_ui_provider_integration_bridge_cli() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        review_path = root / "runtime_receipt_review.json"
        review_path.write_text(json.dumps(fixture_runtime_receipt_review_bridge(), indent=2, sort_keys=True), encoding="utf-8")
        out = root / "out"
        rc = main([
            "--runtime-receipt-review-bridge-json",
            str(review_path),
            "--output-dir",
            str(out),
            "--operator-id",
            "operator.fixture",
            "--integration-note",
            "cli fixture integration",
        ])
        assert rc == 0
        assert len(list(out.glob("*.json"))) == 5


if __name__ == "__main__":
    test_runtime_ui_provider_integration_bridge_cli()
    print("Source Adapter Runtime UI Provider Integration Bridge CLI self-test passed.")
