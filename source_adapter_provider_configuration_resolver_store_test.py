import tempfile
from pathlib import Path
from source_adapter_provider_configuration_resolver import example_source_adapter_provider_configuration_resolver_package
from source_adapter_provider_configuration_resolver_store import store_source_adapter_provider_configuration_resolver_package

with tempfile.TemporaryDirectory() as tmp:
    result = store_source_adapter_provider_configuration_resolver_package(example_source_adapter_provider_configuration_resolver_package(), tmp)
    assert result["store_status"] == "STORED", result
    assert result["output_file_count"] == 3, result
    for row in result["stored_files"]:
        assert Path(row["path"]).exists(), row
        assert row["byte_count"] > 0, row
        assert len(row["sha256"]) == 64, row
print("Source Adapter Provider Configuration Resolver store self-test passed.")
