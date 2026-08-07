from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path

from source_archive_result_intake_test import _handoff_package, _operator_result
from source_archive_result_intake import build_source_archive_result_intake
from source_archive_result_intake_store import store_source_archive_result_intake


def test_store_writes_verified_files() -> None:
    outputs = build_source_archive_result_intake(
        archive_handoff_package=_handoff_package(),
        operator_archive_results=[_operator_result()],
    )
    with TemporaryDirectory() as tmp:
        receipt = store_source_archive_result_intake(outputs.as_dict(), tmp)
        assert receipt["store_status"] == "STORED"
        assert receipt["verification"]["verified"] is True
        assert receipt["output_file_count"] == 4
        for stored in receipt["stored_files"]:
            path = Path(tmp) / stored["filename"]
            assert path.exists()
            assert stored["byte_count"] == len(path.read_bytes())
            assert "/" not in stored["filename"] and "\\" not in stored["filename"]


if __name__ == "__main__":
    test_store_writes_verified_files()
    print("Source Archive Result Intake store self-test passed.")
