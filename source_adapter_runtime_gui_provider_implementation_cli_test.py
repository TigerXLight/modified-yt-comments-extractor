from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_adapter_next_roadmap_work_order_execution_closeout import example_next_roadmap_work_order_execution_closeout_package
from source_adapter_runtime_gui_provider_implementation_cli import main


def main_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "work_order.json"
        output_dir = Path(tmp) / "out"
        input_path.write_text(json.dumps(example_next_roadmap_work_order_execution_closeout_package()), encoding="utf-8")
        rc = main([
            "--next-roadmap-work-order-execution-json", str(input_path),
            "--output-dir", str(output_dir),
            "--operator-id", "cli_tester",
            "--implementation-note", "CLI fixture run.",
        ])
        assert rc == 0
        assert len(list(output_dir.glob("*.json"))) == 8
    print("Source Adapter Runtime GUI Provider Implementation CLI self-test passed.")


if __name__ == "__main__":
    main_test()
