from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_adapter_capture_setup import demo_source_selection_package
from source_adapter_capture_setup_store import store_source_adapter_capture_setup


def test_store_source_adapter_capture_setup() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        summary = store_source_adapter_capture_setup(demo_source_selection_package(), tmpdir)
        assert summary["schema_version"] == "source_adapter_capture_setup_store_v1"
        assert summary["store_status"] == "STORED"
        assert summary["output_file_count"] == 5
        assert summary["verification"]["verified"] is True
        for stored in summary["stored_files"]:
            target = Path(tmpdir) / stored["filename"]
            assert target.exists(), stored
            assert target.stat().st_size == stored["byte_count"]
            json.loads(target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    test_store_source_adapter_capture_setup()
    print("Source Adapter Capture Setup store self-test passed.")
