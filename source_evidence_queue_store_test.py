from __future__ import annotations

import tempfile
from pathlib import Path

from source_evidence_queue import build_source_evidence_queue
from source_evidence_queue_store import store_source_evidence_queue
from source_evidence_queue_test import _package


def main() -> None:
    outputs = build_source_evidence_queue(total_export_package=_package())
    with tempfile.TemporaryDirectory() as tmp:
        receipt = store_source_evidence_queue(outputs.as_dict(), Path(tmp))
        assert receipt["schema_version"] == "source_evidence_queue_store_v1"
        assert receipt["store_status"] == "STORED"
        assert receipt["output_file_count"] == 4
        assert receipt["verification"]["verified"] is True
        for stored in receipt["stored_files"]:
            assert (Path(tmp) / stored["filename"]).exists()
            assert stored["byte_count"] > 0
            assert len(stored["sha256"]) == 64
    print("Source Evidence Queue store self-test passed.")


if __name__ == "__main__":
    main()
