from __future__ import annotations

import tempfile
from pathlib import Path

from lightweight_in_app_browser_capture import build_capture_package
from lightweight_in_app_browser_capture_store import store_capture_package
from lightweight_in_app_browser_capture_verifier import verify_store_receipt


def test_store_writes_expected_outputs() -> None:
    adapter = {"adapter_id": "generic", "display_name": "Generic", "domains": ["example.com"]}
    package = build_capture_package(adapter, "https://example.com/story")
    with tempfile.TemporaryDirectory() as tmp:
        receipt = store_capture_package(package, tmp)
        assert receipt["store_status"] == "STORED"
        assert receipt["output_file_count"] >= 5
        names = {item["filename"] for item in receipt["stored_files"]}
        assert any(name.endswith(".launch_approved_capture.cmd") for name in names)
        assert all(not str(Path(name)).startswith("/") for name in names)
        verification = verify_store_receipt(receipt)
        assert verification["verified"] is True, verification


if __name__ == "__main__":
    test_store_writes_expected_outputs()
    print("Lightweight in-app browser capture store self-test passed.")
