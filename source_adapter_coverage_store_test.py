from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_adapter_coverage import build_source_adapter_coverage
from source_adapter_coverage_store import store_source_adapter_coverage


def test_store_writes_four_stable_artifacts():
    report = build_source_adapter_coverage([
        {"adapter_id": "site_a", "display_name": "Site A", "domains": ["a.example"], "implemented_stages": ["source_discovery"]},
        {"adapter_id": "site_b", "display_name": "Site B", "domains": ["b.example"], "requires_lightweight_browser": False},
    ])
    with tempfile.TemporaryDirectory() as tmp:
        receipt = store_source_adapter_coverage(report, tmp)
        assert receipt["store_status"] == "STORED"
        assert receipt["output_file_count"] == 4
        for item in receipt["stored_files"]:
            path = Path(tmp) / item["filename"]
            assert path.exists()
            assert path.stat().st_size == item["byte_count"]
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert "schema_version" in payload


if __name__ == "__main__":
    test_store_writes_four_stable_artifacts()
    print("Source Adapter coverage framework store self-test passed.")
