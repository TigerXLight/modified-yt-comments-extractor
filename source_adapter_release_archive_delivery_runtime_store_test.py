from pathlib import Path
from source_adapter_release_archive_delivery_runtime_store import store_source_adapter_release_archive_delivery_runtime_package

result = store_source_adapter_release_archive_delivery_runtime_package()
assert result["store_status"] == "STORED"
assert result["output_file_count"] == 5
assert result["delivery_receipt_row_count"] == 20
for meta in result["stored_files"]:
    path = Path(meta["path"])
    assert path.exists(), path
    assert meta["byte_count"] == path.stat().st_size
print("Source Adapter Release Archive Delivery Runtime store self-test passed.")
