from __future__ import annotations

from tempfile import TemporaryDirectory

from source_adapter_release_publish_receipt_runtime_store import write_release_publish_receipt_runtime_package


def test_release_publish_receipt_runtime_store() -> None:
    with TemporaryDirectory() as tmp:
        result = write_release_publish_receipt_runtime_package(tmp, operator_id="store_operator")
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 3
        assert result["verification"]["verified"] is True
        for stored_file in result["stored_files"]:
            assert stored_file["byte_count"] > 0
            assert stored_file["sha256"]


if __name__ == "__main__":
    test_release_publish_receipt_runtime_store()
    print("Source Adapter Release Publish Receipt Runtime store self-test passed.")
