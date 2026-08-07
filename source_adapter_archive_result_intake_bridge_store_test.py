from __future__ import annotations

import tempfile
from pathlib import Path

from source_adapter_archive_result_intake_bridge import build_source_adapter_archive_result_intake_bridge
from source_adapter_archive_result_intake_bridge_store import store_source_adapter_archive_result_intake_bridge
from source_adapter_archive_result_intake_bridge_test import fixture_archive_handoff_bridge, fixture_operator_results


def main() -> None:
    archive_handoff_bridge = fixture_archive_handoff_bridge()
    package = build_source_adapter_archive_result_intake_bridge(archive_handoff_bridge, fixture_operator_results(archive_handoff_bridge))
    with tempfile.TemporaryDirectory() as tmp:
        receipt = store_source_adapter_archive_result_intake_bridge(package, Path(tmp))
        assert receipt["schema_version"] == "source_adapter_archive_result_intake_bridge_store_v1"
        assert receipt["store_status"] == "STORED"
        assert receipt["verification"]["verified"] is True
        assert receipt["output_file_count"] == 5
        assert all((Path(tmp) / item["filename"]).exists() for item in receipt["stored_files"])
        assert any(item["role"] == "source_adapter_archive_review_batch_handoff" for item in receipt["stored_files"])


if __name__ == "__main__":
    main()
    print("Source Adapter Archive Result Intake Bridge store self-test passed.")
