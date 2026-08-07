from __future__ import annotations

import tempfile
from pathlib import Path

from source_adapter_archive_review_bridge import build_source_adapter_archive_review_bridge
from source_adapter_archive_review_bridge_store import store_source_adapter_archive_review_bridge
from source_adapter_archive_review_bridge_test import fixture_archive_result_intake_bridge


def main() -> None:
    package = build_source_adapter_archive_review_bridge(
        fixture_archive_result_intake_bridge(),
        archive_reviewer_decision={"decision": "APPROVED"},
    )
    with tempfile.TemporaryDirectory() as tmp:
        receipt = store_source_adapter_archive_review_bridge(package, Path(tmp))
        assert receipt["schema_version"] == "source_adapter_archive_review_bridge_store_v1"
        assert receipt["store_status"] == "STORED"
        assert receipt["archive_review_bridge_status"] == "SHARED_ARCHIVE_REVIEWS_BUILT"
        assert receipt["archive_review_count"] == 1
        assert receipt["output_file_count"] == 5
        assert receipt["verification"]["verified"] is True
        assert any(item["role"] == "source_adapter_pipeline_closeout_batch_handoff" for item in receipt["stored_files"])
        assert len(list(Path(tmp).glob("*.json"))) == 5


if __name__ == "__main__":
    main()
    print("Source Adapter Archive Review Bridge store self-test passed.")
