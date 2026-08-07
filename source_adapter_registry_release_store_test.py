from tempfile import TemporaryDirectory

from source_adapter_registry_release_store import store_source_adapter_registry_release
from source_adapter_registry_release_test import _registry_update_package


def test_store_writes_release_outputs():
    with TemporaryDirectory() as tmp:
        summary = store_source_adapter_registry_release(_registry_update_package(), tmp)
        assert summary["schema_version"] == "source_adapter_registry_release_store_v1"
        assert summary["store_status"] == "STORED"
        assert summary["output_file_count"] == 5
        assert summary["verification"]["verified"] is True
        filenames = {item["filename"] for item in summary["stored_files"]}
        assert any(name.endswith("source_adapter_frozen_registry.json") for name in filenames)
        assert any(name.endswith("source_adapter_registry_rollout_handoff.json") for name in filenames)


if __name__ == "__main__":
    test_store_writes_release_outputs()
    print("Source Adapter Registry Release store self-test passed.")
