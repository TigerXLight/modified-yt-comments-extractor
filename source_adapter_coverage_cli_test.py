from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_adapter_coverage_cli import main


def test_cli_writes_coverage_artifacts():
    with tempfile.TemporaryDirectory() as tmp:
        spec = Path(tmp) / "adapters.json"
        out = Path(tmp) / "out"
        spec.write_text(json.dumps({"adapters": [
            {"adapter_id": "msn_manual", "display_name": "MSN", "domains": ["msn.com"], "implemented_stages": ["source_discovery"]},
            {"adapter_id": "news_site", "display_name": "News Site", "domains": ["news.example"]},
        ]}), encoding="utf-8")
        status = main(["--adapter-spec", str(spec), "--output-dir", str(out)])
        assert status == 0
        assert len(list(out.glob("*.json"))) == 4


def test_cli_print_report_mode():
    with tempfile.TemporaryDirectory() as tmp:
        spec = Path(tmp) / "adapter.json"
        spec.write_text(json.dumps({"adapter_id": "single", "display_name": "Single", "domains": ["single.example"]}), encoding="utf-8")
        status = main(["--adapter-spec", str(spec), "--output-dir", str(Path(tmp) / "out"), "--print-report"])
        assert status == 0


if __name__ == "__main__":
    test_cli_writes_coverage_artifacts()
    test_cli_print_report_mode()
    print("Source Adapter coverage framework CLI self-test passed.")
