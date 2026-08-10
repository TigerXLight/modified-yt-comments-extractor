from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_manual_validation import (
    DEFAULT_CHECKS,
    build_msn_manual_validation_result,
    write_msn_manual_validation_result,
    write_msn_manual_validation_template,
)


def test_manual_validation_template_and_result_outputs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        template = root / "template.json"
        write_msn_manual_validation_template(template, source_url="https://www.msn.com/example", capture_root=str(root))
        data = json.loads(template.read_text(encoding="utf-8"))
        assert len(data["checks"]) == len(DEFAULT_CHECKS)
        for check in data["checks"]:
            check["status"] = "PASS"
        data["checks"][1]["status"] = "PARTIAL"
        completed = root / "completed.json"
        completed.write_text(json.dumps(data, indent=2), encoding="utf-8")
        paths = write_msn_manual_validation_result(completed, output_dir=root / "result")
        result = json.loads(Path(paths["manual_validation_json"]).read_text(encoding="utf-8"))
        assert result["overall_status"] == "PARTIAL"
        assert Path(paths["manual_validation_markdown"]).is_file()
        assert "Google Street View" in Path(paths["manual_validation_markdown"]).read_text(encoding="utf-8")


def test_manual_validation_failure_blocks_completion() -> None:
    data = {
        "checks": {
            "article_title_body_visible": "PASS",
            "media_inventory_created": "FAIL",
        }
    }
    result = build_msn_manual_validation_result(data)
    assert result.overall_status == "FAIL"
    assert "media_inventory_created" in result.blocking_failures


if __name__ == "__main__":
    test_manual_validation_template_and_result_outputs()
    test_manual_validation_failure_blocks_completion()
    print("MSN manual validation intake self-test passed.")
