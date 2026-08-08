from __future__ import annotations

from tempfile import TemporaryDirectory

from source_adapter_source_pipeline_completion_runtime_store import write_source_pipeline_completion_runtime_package


def test_source_pipeline_completion_runtime_store() -> None:
    with TemporaryDirectory() as tmp:
        result = write_source_pipeline_completion_runtime_package(tmp, operator_id="store_operator")
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 3
        assert result["verification"]["verified"] is True
        for stored_file in result["stored_files"]:
            assert stored_file["byte_count"] > 0
            assert stored_file["sha256"]


if __name__ == "__main__":
    test_source_pipeline_completion_runtime_store()
    print("Source Adapter Source Pipeline Completion Runtime store self-test passed.")
