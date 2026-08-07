from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_adapter_fixture_authoring_cli import main


def test_cli_store_and_verify() -> None:
    matrix = {
        "fixture_matrix": {
            "rows": [
                {
                    "adapter_id": "article",
                    "fixture_types": ["saved_article_html_or_text", "expected_pipeline_closeout_json"],
                    "shared_pipeline_stages": ["artifact_collection", "pipeline_closeout"],
                }
            ]
        }
    }
    with tempfile.TemporaryDirectory() as tmp:
        matrix_path = Path(tmp) / "matrix.json"
        output_dir = Path(tmp) / "out"
        matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
        assert main(["--fixture-matrix-json", str(matrix_path), "--output-dir", str(output_dir), "--json"]) == 0
        package_path = next(output_dir.glob("*.source_adapter_fixture_authoring_package.json"))
        assert main(["--verify", str(package_path), "--json"]) == 0


if __name__ == "__main__":
    test_cli_store_and_verify()
    print("Source Adapter Fixture Authoring CLI self-test passed.")
