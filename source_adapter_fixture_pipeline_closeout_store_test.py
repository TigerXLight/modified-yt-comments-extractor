from __future__ import annotations

import tempfile

from source_adapter_fixture_pipeline_closeout_store import store_source_adapter_fixture_pipeline_closeout
from source_adapter_fixture_pipeline_closeout_test import _passed_pipeline


def test_store_writes_closeout_outputs() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        record = store_source_adapter_fixture_pipeline_closeout(_passed_pipeline(), tmpdir)
        assert record["store_status"] == "STORED"
        assert record["output_file_count"] == 5
        assert record["verification"]["verified"] is True
        assert len(record["stored_files"]) == 5


if __name__ == "__main__":
    test_store_writes_closeout_outputs()
    print("Source Adapter Fixture Pipeline Closeout store self-test passed.")
