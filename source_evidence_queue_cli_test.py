from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_evidence_queue_cli import main as cli_main
from source_evidence_queue_test import _package


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = root / "package.json"
        package_path.write_text(json.dumps(_package(), sort_keys=True), encoding="utf-8")
        output_dir = root / "out"
        rc = cli_main([
            "--total-export-package-json",
            str(package_path),
            "--queue-note",
            "cli fixture",
            "--output-dir",
            str(output_dir),
        ])
        assert rc == 0
        outputs = list(output_dir.glob("*.json"))
        assert len(outputs) == 4
    print("Source Evidence Queue CLI self-test passed.")


if __name__ == "__main__":
    main()
