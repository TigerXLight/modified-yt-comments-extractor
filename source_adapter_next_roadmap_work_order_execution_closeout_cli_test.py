import json
import subprocess
import sys
import tempfile
from pathlib import Path

from source_adapter_next_roadmap_section_selection_closeout import example_next_roadmap_section_selection_closeout_package


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "selection.json"
        output_dir = Path(tmp) / "out"
        input_path.write_text(json.dumps(example_next_roadmap_section_selection_closeout_package()), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "source_adapter_next_roadmap_work_order_execution_closeout_cli.py", "--next-roadmap-section-selection-json", str(input_path), "--output-dir", str(output_dir), "--operator-id", "cli_tester"],
            check=True,
            text=True,
            capture_output=True,
        )
        payload = json.loads(completed.stdout)
        assert payload["store_status"] == "STORED"
        assert payload["verification"]["verified"] is True
        assert payload["output_file_count"] == 10
    print("Source Adapter Next Roadmap Work Order Execution Closeout CLI self-test passed.")


if __name__ == "__main__":
    main()
