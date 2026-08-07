from pathlib import Path
from tempfile import TemporaryDirectory

from source_adapter_registry_rollout_store import store_source_adapter_registry_rollout
from source_adapter_registry_rollout_test import _registry_release_package


def test_store_writes_registry_rollout_artifacts():
    with TemporaryDirectory() as tmp:
        summary = store_source_adapter_registry_rollout(_registry_release_package(), tmp)
        assert summary["store_status"] == "STORED"
        assert summary["output_file_count"] == 5
        assert summary["verification"]["verified"] is True
        files = list(Path(tmp).glob("*.json"))
        assert len(files) == 5
        assert all(item["byte_count"] > 0 for item in summary["stored_files"])


if __name__ == "__main__":
    test_store_writes_registry_rollout_artifacts()
    print("Source Adapter Registry Rollout store self-test passed.")
