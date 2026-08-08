from __future__ import annotations

from pathlib import Path

from source_adapter_named_site_smoke_execution_store import store_source_adapter_named_site_smoke_execution_package


def test_store_named_site_smoke_execution_package() -> None:
    result = store_source_adapter_named_site_smoke_execution_package()
    assert result["store_status"] == "STORED"
    assert result["named_site_execution_site_count"] == 5
    assert result["named_site_provider_action_receipt_row_count"] == 25
    assert result["verification"]["verified"] is True
    for item in result["stored_files"]:
        assert Path(item["path"]).exists()
        assert item["byte_count"] > 0


if __name__ == "__main__":
    test_store_named_site_smoke_execution_package()
    print("Source Adapter Named-Site Smoke Execution store self-test passed.")
