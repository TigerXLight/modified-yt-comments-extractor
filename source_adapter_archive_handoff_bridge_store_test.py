from __future__ import annotations

import tempfile
from pathlib import Path

from source_adapter_archive_handoff_bridge import build_source_adapter_archive_handoff_bridge
from source_adapter_archive_handoff_bridge_store import store_source_adapter_archive_handoff_bridge
from source_adapter_archive_handoff_bridge_test import fixture_release_audit_bridge


def main() -> None:
    package = build_source_adapter_archive_handoff_bridge(fixture_release_audit_bridge(), archive_providers=["archive_today"])
    with tempfile.TemporaryDirectory() as tmp:
        receipt = store_source_adapter_archive_handoff_bridge(package, tmp)
        assert receipt["schema_version"] == "source_adapter_archive_handoff_bridge_store_v1"
        assert receipt["store_status"] == "STORED"
        assert receipt["archive_handoff_count"] == 1
        assert receipt["output_file_count"] == 5
        assert receipt["verification"]["verified"] is True
        for stored in receipt["stored_files"]:
            assert (Path(tmp) / stored["filename"]).exists()
            assert stored["byte_count"] > 0
            assert len(stored["sha256"]) == 64


if __name__ == "__main__":
    main()
    print("Source Adapter Archive Handoff Bridge store self-test passed.")
