from __future__ import annotations

import tempfile
from pathlib import Path

from source_total_export_package import build_source_total_export_package
from source_total_export_package_store import store_source_total_export_package
from source_total_export_package_test import _fixture_capture_bundle


def test_store_source_total_export_package() -> None:
    outputs = build_source_total_export_package(capture_bundle=_fixture_capture_bundle())
    with tempfile.TemporaryDirectory() as tmpdir:
        receipt = store_source_total_export_package(outputs.as_dict(), Path(tmpdir))
        assert receipt["schema_version"] == "source_total_export_package_store_v1"
        assert receipt["store_status"] == "STORED"
        assert receipt["output_file_count"] == 4
        assert receipt["verification"]["verified"] is True
        for stored in receipt["stored_files"]:
            path = Path(tmpdir) / stored["filename"]
            assert path.exists()
            assert path.stat().st_size == stored["byte_count"]


if __name__ == "__main__":
    test_store_source_total_export_package()
    print("Source Total Export package store self-test passed.")
