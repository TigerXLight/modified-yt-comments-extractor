import json
import subprocess
import sys
from tempfile import TemporaryDirectory


def main() -> None:
    with TemporaryDirectory() as tmp:
        output = subprocess.check_output(
            [sys.executable, "source_adapter_release_regression_next_roadmap_closeout_cli.py", "--output-dir", tmp, "--operator-id", "cli_operator"],
            text=True,
        )
    payload = json.loads(output)
    assert payload["store_status"] == "STORED"
    assert payload["verification"]["verified"] is True
    assert payload["verification"]["handoff_status"] == "SOURCE_ADAPTER_RELEASE_REGRESSION_AND_NEXT_ROADMAP_HANDOFF_READY"
    print("Source Adapter Release Regression Next Roadmap Closeout CLI self-test passed.")


if __name__ == "__main__":
    main()
