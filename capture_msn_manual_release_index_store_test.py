from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_msn_manual_release_index import build_msn_manual_release_index
from capture_msn_manual_release_index_store import store_msn_manual_release_index
from capture_msn_manual_release_index_test import _approved_release, _store_report


def test_store_release_index_outputs_safe_files() -> None:
    report = build_msn_manual_release_index(_approved_release(), release_package_store_report=_store_report())
    with tempfile.TemporaryDirectory() as temp_dir:
        store_report = store_msn_manual_release_index(report, temp_dir)
        assert store_report.schema_version == "msn_manual_release_index_store_v1"
        assert store_report.store_status == "STORED"
        assert store_report.output_file_count == 3
        filenames = {stored.filename for stored in store_report.stored_files}
        assert any(name.endswith(".release_index.json") for name in filenames)
        assert any(name.endswith(".release_inventory.json") for name in filenames)
        assert any(name.endswith(".release_queue_update.json") for name in filenames)
        for stored in store_report.stored_files:
            assert "\\" not in stored.filename
            assert "/" not in stored.filename
            data = (Path(temp_dir) / stored.filename).read_bytes()
            assert len(data) == stored.byte_count
            assert stored.sha256
            json.loads(data.decode("utf-8"))


if __name__ == "__main__":
    test_store_release_index_outputs_safe_files()
    print("MSN manual release index store self-test passed.")
