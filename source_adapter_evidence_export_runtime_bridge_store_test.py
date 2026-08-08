from pathlib import Path
from source_adapter_evidence_export_runtime_bridge_store import store_source_adapter_evidence_export_runtime_bridge_package

result = store_source_adapter_evidence_export_runtime_bridge_package()
assert result["store_status"] == "STORED"
assert result["output_file_count"] == 7
for meta in result["stored_files"]:
    path = Path(meta["path"])
    assert path.exists(), path
    assert meta["byte_count"] == path.stat().st_size
    assert len(meta["sha256"]) == 64
print("Source Adapter Evidence Export Runtime Bridge store self-test passed.")
