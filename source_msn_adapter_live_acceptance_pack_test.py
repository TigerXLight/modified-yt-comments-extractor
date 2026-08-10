from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_live_acceptance_pack import main, write_live_acceptance_pack


def test_live_acceptance_pack_writes_all_templates() -> None:
    with tempfile.TemporaryDirectory() as td:
        files = write_live_acceptance_pack(Path(td), article_url="https://www.msn.com/example", output_folder="C:/captures/example")
        assert set(files) == {"checklist", "result_template_json", "result_template_md", "decision_guide"}
        for path in files.values():
            assert Path(path).exists()
        data = json.loads(Path(files["result_template_json"]).read_text(encoding="utf-8"))
        assert data["article_url"] == "https://www.msn.com/example"
        assert data["output_folder"] == "C:/captures/example"
        assert data["republisher_distinction_preserved"] == "UNKNOWN"
        assert "The Independent" in Path(files["checklist"]).read_text(encoding="utf-8")


def test_live_acceptance_pack_cli() -> None:
    with tempfile.TemporaryDirectory() as td:
        assert main(["--output", td, "--article-url", "https://www.msn.com/example"]) == 0
        assert (Path(td) / "01_MSN_LIVE_ACCEPTANCE_CHECKLIST.md").exists()


if __name__ == "__main__":
    test_live_acceptance_pack_writes_all_templates()
    test_live_acceptance_pack_cli()
    print("MSN live acceptance pack self-test passed.")
