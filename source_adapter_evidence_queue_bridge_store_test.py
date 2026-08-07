from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_adapter_evidence_queue_bridge import build_source_adapter_evidence_queue_bridge
from source_adapter_evidence_queue_bridge_store import store_source_adapter_evidence_queue_bridge
from source_adapter_evidence_queue_bridge_test import fixture_total_export_bridge


def main() -> None:
    package = build_source_adapter_evidence_queue_bridge(fixture_total_export_bridge())
    with tempfile.TemporaryDirectory() as tmp:
        result = store_source_adapter_evidence_queue_bridge(package, tmp)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 5
        assert result["verification"]["verified"] is True
        files = sorted(Path(tmp).iterdir())
        assert len(files) == 5
        for file_path in files:
            data = file_path.read_bytes()
            assert result["source_adapter_evidence_queue_bridge_id"].encode() in data or b"schema_version" in data
            json.loads(data.decode("utf-8"))


if __name__ == "__main__":
    main()
    print("Source Adapter Evidence Queue Bridge store self-test passed.")
