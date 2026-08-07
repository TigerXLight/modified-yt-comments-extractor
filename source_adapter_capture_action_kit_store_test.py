from __future__ import annotations

import tempfile

from source_adapter_capture_action_kit import build_source_adapter_capture_action_kit
from source_adapter_capture_action_kit_store import store_source_adapter_capture_action_kit


def test_store_writes_five_files() -> None:
    package = build_source_adapter_capture_action_kit(
        {"adapters": [{"adapter_id": "article", "artifact_roles": ["article_html_or_text"]}]}
    )
    with tempfile.TemporaryDirectory() as tmp:
        result = store_source_adapter_capture_action_kit(package, tmp)
    assert result["store_status"] == "STORED"
    assert result["output_file_count"] == 5
    assert result["verification"]["verified"] is True
    assert all(row["byte_count"] > 0 and len(row["sha256"]) == 64 for row in result["stored_files"])


if __name__ == "__main__":
    test_store_writes_five_files()
    print("Source Adapter Capture Action Kit store self-test passed.")
