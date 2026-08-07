import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from source_adapter_registry_rollout import write_json_file
from source_adapter_registry_rollout_cli import main
from source_adapter_registry_rollout_test import _registry_release_package


def test_cli_writes_registry_rollout_package():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_path = tmp_path / "registry_release_package.json"
        output_dir = tmp_path / "out"
        write_json_file(input_path, _registry_release_package())
        buffer = StringIO()
        with patch("sys.stdout", buffer):
            exit_code = main(["--registry-release-package", str(input_path), "--output-dir", str(output_dir), "--json"])
        assert exit_code == 0
        summary = json.loads(buffer.getvalue())
        assert summary["registry_rollout_status"] == "ADAPTER_REGISTRY_ROLLOUT_READY"
        assert summary["output_file_count"] == 5
        assert len(list(output_dir.glob("*.json"))) == 5


if __name__ == "__main__":
    test_cli_writes_registry_rollout_package()
    print("Source Adapter Registry Rollout CLI self-test passed.")
