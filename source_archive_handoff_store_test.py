from __future__ import annotations

import tempfile
from pathlib import Path

from source_archive_handoff import build_source_archive_handoff
from source_archive_handoff_store import store_source_archive_handoff
from source_archive_handoff_test import _release_audit_report


def test_source_archive_handoff_store_writes_receipts() -> None:
    outputs = build_source_archive_handoff(
        release_audit_report=_release_audit_report(),
        archive_providers=["archive_today"],
    )
    with tempfile.TemporaryDirectory() as tmp:
        receipt = store_source_archive_handoff(outputs.as_dict(), tmp)
        assert receipt["schema_version"] == "source_archive_handoff_store_v1"
        assert receipt["store_status"] == "STORED"
        assert receipt["output_file_count"] == 5
        assert receipt["verification"]["verified"] is True
        for stored in receipt["stored_files"]:
            assert (Path(tmp) / stored["filename"]).exists()
            assert stored["byte_count"] > 0
            assert len(stored["sha256"]) == 64


if __name__ == "__main__":
    test_source_archive_handoff_store_writes_receipts()
    print("Source Archive Handoff store self-test passed.")
