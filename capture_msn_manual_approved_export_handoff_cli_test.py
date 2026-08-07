from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_msn_manual_approved_export_handoff_cli import main as cli_main
from capture_msn_manual_approved_export_handoff_test import _decision


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        decision_path = base / "decision.json"
        decision_path.write_text(json.dumps(_decision()), encoding="utf-8")
        rc = cli_main(["--decision-json", str(decision_path), "--output-dir", str(base / "out"), "--operator-run-id", "cli_run"])
        assert rc == 0
        outputs = list((base / "out").glob("*.json"))
        assert len(outputs) == 2
    print("MSN manual approved export handoff CLI self-test passed.")


if __name__ == "__main__":
    main()
