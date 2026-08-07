from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_msn_manual_approved_release_package import build_msn_manual_approved_release_package
from capture_msn_manual_approved_release_package_store import store_msn_manual_approved_release_package
from capture_msn_manual_approved_release_package_test import _handoff, _package_store


def test_store_release_package() -> None:
    report = build_msn_manual_approved_release_package(_handoff(), package_store_report=_package_store())
    with tempfile.TemporaryDirectory() as tmp:
        store = store_msn_manual_approved_release_package(report, tmp)
        assert store.schema_version == "msn_manual_approved_release_package_store_v1"
        assert store.output_file_count == 3
        names = {stored.filename for stored in store.stored_files}
        assert any(name.endswith(".approved_release_package.json") for name in names)
        assert any(name.endswith(".approved_release_manifest.json") for name in names)
        assert any(name.endswith(".approved_release_queue_update.json") for name in names)
        for stored in store.stored_files:
            data = (Path(tmp) / stored.filename).read_bytes()
            assert len(data) == stored.byte_count
            payload = json.loads(data.decode("utf-8"))
            assert payload["file_role"].startswith("approved_release")


if __name__ == "__main__":
    test_store_release_package()
    print("MSN manual approved release package store self-test passed.")
