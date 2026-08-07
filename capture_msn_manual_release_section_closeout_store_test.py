from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_msn_manual_release_section_closeout import build_msn_manual_release_section_closeout
from capture_msn_manual_release_section_closeout_store import (
    msn_manual_release_section_closeout_store_report_to_json,
    store_msn_manual_release_section_closeout,
)
from capture_msn_manual_release_section_closeout_test import _bundle, _store


def test_store_closeout_writes_safe_outputs() -> None:
    report = build_msn_manual_release_section_closeout(_bundle(), release_export_bundle_store_report=_store())
    with tempfile.TemporaryDirectory() as temp_dir:
        store_report = store_msn_manual_release_section_closeout(report, temp_dir)
        payload = msn_manual_release_section_closeout_store_report_to_json(store_report)
        assert payload["store_status"] == "STORED"
        assert payload["output_file_count"] == 4
        for stored_file in payload["stored_files"]:
            assert "\\" not in stored_file["filename"]
            assert "/" not in stored_file["filename"]
            path = Path(temp_dir) / stored_file["filename"]
            assert path.exists()
            assert len(stored_file["sha256"]) == 64
            assert stored_file["byte_count"] == len(path.read_bytes())
            json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    test_store_closeout_writes_safe_outputs()
    print("MSN manual release section closeout store self-test passed.")
