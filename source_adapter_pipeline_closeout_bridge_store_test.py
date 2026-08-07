from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from source_adapter_pipeline_closeout_bridge import build_source_adapter_pipeline_closeout_bridge
from source_adapter_pipeline_closeout_bridge_store import store_source_adapter_pipeline_closeout_bridge
from source_adapter_pipeline_closeout_bridge_test import fixture_archive_review_bridge


def test_store_source_adapter_pipeline_closeout_bridge() -> None:
    package = build_source_adapter_pipeline_closeout_bridge(fixture_archive_review_bridge())
    with TemporaryDirectory() as tmp:
        result = store_source_adapter_pipeline_closeout_bridge(package, tmp)
        assert result["store_status"] == "STORED"
        assert result["pipeline_closeout_count"] == 1
        assert result["output_file_count"] == 5
        assert result["verification"]["verified"] is True
        for stored in result["stored_files"]:
            path = Path(tmp) / stored["filename"]
            assert path.exists()
            assert path.stat().st_size == stored["byte_count"]
            assert len(stored["sha256"]) == 64


if __name__ == "__main__":
    test_store_source_adapter_pipeline_closeout_bridge()
    print("Source Adapter Pipeline Closeout Bridge store self-test passed.")
