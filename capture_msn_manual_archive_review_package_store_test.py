import json
import tempfile
from pathlib import Path

from capture_msn_manual_archive_review_package import build_msn_manual_archive_review_package
from capture_msn_manual_archive_review_package_cli import _fixture_intake
from capture_msn_manual_archive_review_package_store import store_msn_manual_archive_review_package


def test_store_archive_review_package_outputs_four_safe_json_files():
    package = build_msn_manual_archive_review_package(_fixture_intake())
    with tempfile.TemporaryDirectory() as tmp:
        receipt = store_msn_manual_archive_review_package(package, tmp)
        assert receipt["schema_version"] == "msn_manual_archive_review_package_store_v1"
        assert receipt["store_status"] == "STORED"
        assert receipt["output_file_count"] == 4
        for stored in receipt["stored_files"]:
            assert "\\" not in stored["filename"]
            assert "/" not in stored["filename"]
            payload = json.loads((Path(tmp) / stored["filename"]).read_text(encoding="utf-8"))
            assert payload["file_role"].startswith("msn_manual_archive")


if __name__ == "__main__":
    test_store_archive_review_package_outputs_four_safe_json_files()
    print("MSN manual archive review package store self-test passed.")
