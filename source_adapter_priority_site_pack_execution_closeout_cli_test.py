import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        completed = subprocess.run(
            [
                sys.executable,
                "source_adapter_priority_site_pack_execution_closeout_cli.py",
                "--output-dir",
                temp_dir,
                "--operator-id",
                "cli_tester",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        assert payload["store_status"] == "STORED"
        assert payload["verification"]["verified"] is True
        assert payload["priority_site_pack_count"] >= 7
        assert len(list(Path(temp_dir).glob("*.json"))) == 5
    print("Source Adapter Priority Site Pack Execution Closeout CLI self-test passed.")


if __name__ == "__main__":
    main()
