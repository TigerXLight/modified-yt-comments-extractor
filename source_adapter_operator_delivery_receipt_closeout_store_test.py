from pathlib import Path
from source_adapter_operator_delivery_receipt_closeout_store import store_source_adapter_operator_delivery_receipt_closeout_package

result = store_source_adapter_operator_delivery_receipt_closeout_package()
assert result["store_status"] == "STORED"
assert result["output_file_count"] == 6
assert result["release_section_completion_ready"] is True
for meta in result["stored_files"]:
    path = Path(meta["path"])
    assert path.exists(), path
    assert meta["byte_count"] == path.stat().st_size
print("Source Adapter Operator Delivery Receipt Closeout store self-test passed.")
