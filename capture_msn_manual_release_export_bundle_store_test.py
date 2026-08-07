from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_msn_manual_release_export_bundle import build_msn_manual_release_export_bundle
from capture_msn_manual_release_export_bundle_store import (
    msn_manual_release_export_bundle_store_report_to_json,
    store_msn_manual_release_export_bundle,
)
from capture_msn_manual_release_export_bundle_test import _release_index


def test_store_release_export_bundle() -> None:
    report = build_msn_manual_release_export_bundle(_release_index())
    with tempfile.TemporaryDirectory() as tmp:
        store = store_msn_manual_release_export_bundle(report, tmp)
        payload = msn_manual_release_export_bundle_store_report_to_json(store)
        assert payload["store_status"] == "STORED"
        assert payload["output_file_count"] == 3
        assert {item["role"] for item in payload["stored_files"]} == {
            "msn_manual_release_export_bundle",
            "msn_manual_release_export_manifest",
            "msn_manual_release_export_queue_update",
        }
        for item in payload["stored_files"]:
            stored = Path(tmp) / item["filename"]
            assert stored.exists()
            assert len(stored.read_bytes()) == item["byte_count"]
            json.loads(stored.read_text(encoding="utf-8"))


if __name__ == "__main__":
    test_store_release_export_bundle()
    print("MSN manual release export bundle store self-test passed.")
