from __future__ import annotations

import tempfile
from pathlib import Path

from source_adapter_approved_release_bridge import build_source_adapter_approved_release_bridge
from source_adapter_approved_release_bridge_store import store_source_adapter_approved_release_bridge
from source_adapter_approved_release_bridge_test import fixture_evidence_review_bridge


def main() -> None:
    package = build_source_adapter_approved_release_bridge(fixture_evidence_review_bridge())
    with tempfile.TemporaryDirectory() as tmp:
        result = store_source_adapter_approved_release_bridge(package, tmp)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 5
        assert result["verification"]["verified"] is True
        for entry in result["stored_files"]:
            path = Path(tmp) / entry["filename"]
            assert path.exists()
            assert path.stat().st_size == entry["byte_count"]
            assert entry["sha256"]


if __name__ == "__main__":
    main()
    print("Source Adapter Approved Release Bridge store self-test passed.")
