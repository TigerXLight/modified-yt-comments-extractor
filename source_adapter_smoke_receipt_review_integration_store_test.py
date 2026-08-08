from __future__ import annotations

from pathlib import Path

from source_adapter_smoke_receipt_review_integration_store import store_source_adapter_smoke_receipt_review_integration_package


def test_store_smoke_receipt_review_integration_package() -> None:
    result = store_source_adapter_smoke_receipt_review_integration_package()
    assert result["store_status"] == "STORED"
    assert result["smoke_receipt_review_decision_row_count"] == 25
    assert result["smoke_receipt_evidence_integration_row_count"] == 5
    assert result["verification"]["verified"] is True
    for item in result["stored_files"]:
        assert Path(item["path"]).exists()
        assert item["byte_count"] > 0


if __name__ == "__main__":
    test_store_smoke_receipt_review_integration_package()
    print("Source Adapter Smoke Receipt Review Integration store self-test passed.")
