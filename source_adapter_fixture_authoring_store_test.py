from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_adapter_fixture_authoring_store import store_source_adapter_fixture_authoring


def test_store_writes_expected_files() -> None:
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
        result = store_source_adapter_fixture_authoring(matrix, tmp)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 5
        for item in result["stored_files"]:
            path = Path(tmp) / item["filename"]
            assert path.exists()
            assert item["byte_count"] == len(path.read_bytes())
            assert json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    test_store_writes_expected_files()
    print("Source Adapter Fixture Authoring store self-test passed.")
