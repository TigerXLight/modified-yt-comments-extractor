from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from capture_msn_manual_evidence_review_decision_cli import main
from capture_msn_manual_evidence_review_decision_test import _package


def test_cli_records_and_stores_decision() -> None:
    package = _package()
    completed = [action["action_id"] for action in package["review_actions"]]
    with tempfile.TemporaryDirectory() as tmp:
        package_path = Path(tmp) / "review_package.json"
        output_dir = Path(tmp) / "out"
        package_path.write_text(json.dumps(package), encoding="utf-8")
        argv = [
            "--review-package-json",
            str(package_path),
            "--output-dir",
            str(output_dir),
            "--decision",
            "APPROVED",
        ]
        for action_id in completed:
            argv.extend(["--completed-action", action_id])
        with patch("sys.stdout") as stdout:
            assert main(argv) == 0
        output = "".join(call.args[0] for call in stdout.write.call_args_list)
        payload = json.loads(output)
        assert payload["output_file_count"] == 2
        assert payload["queue_item_id"] == "msn_queue_001"


if __name__ == "__main__":
    test_cli_records_and_stores_decision()
    print("MSN manual Evidence Review decision CLI self-test passed.")
