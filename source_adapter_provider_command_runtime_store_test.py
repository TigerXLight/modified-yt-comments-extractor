from __future__ import annotations

from pathlib import Path

from source_adapter_provider_command_runtime_store import store_source_adapter_provider_command_runtime_package


def test_store_provider_command_runtime_package() -> None:
    result = store_source_adapter_provider_command_runtime_package()
    assert result["store_status"] == "STORED"
    assert result["provider_command_request_row_count"] == 25
    assert result["provider_command_execution_receipt_row_count"] == 25
    assert result["verification"]["verified"] is True
    for item in result["stored_files"]:
        assert Path(item["path"]).exists()
        assert item["byte_count"] > 0
        assert len(item["sha256"]) == 64


if __name__ == "__main__":
    test_store_provider_command_runtime_package()
    print("Source Adapter Provider Command Runtime store self-test passed.")
