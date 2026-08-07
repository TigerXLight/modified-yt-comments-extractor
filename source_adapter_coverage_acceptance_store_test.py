from __future__ import annotations

import tempfile
from pathlib import Path

from source_adapter_coverage_acceptance_store import store_source_adapter_coverage_acceptance
from source_adapter_coverage_acceptance_test import _accepted_closeout


def test_store_writes_expected_outputs() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        record = store_source_adapter_coverage_acceptance(_accepted_closeout(), temp_dir)
        assert record["store_status"] == "STORED"
        assert record["output_file_count"] == 4
        assert record["verification"]["verified"] is True
        for item in record["stored_files"]:
            assert (Path(temp_dir) / item["filename"]).exists()
            assert item["byte_count"] > 0
            assert len(item["sha256"]) == 64


if __name__ == "__main__":
    test_store_writes_expected_outputs()
    print("Source Adapter Coverage Acceptance store self-test passed.")
