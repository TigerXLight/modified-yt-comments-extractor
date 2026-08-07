from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_msn_manual_action_total_export_pipeline import build_msn_manual_action_total_export_pipeline
from capture_msn_manual_action_total_export_pipeline_store import (
    msn_manual_action_total_export_pipeline_store_result_to_json,
    store_msn_manual_action_total_export_pipeline_result,
)


def test_pipeline_store_writes_safe_report_and_manifest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        article = root / "article.txt"
        article.write_text("Headline\nArticle body copied by operator with enough text.", encoding="utf-8")
        result = build_msn_manual_action_total_export_pipeline(
            source_url="https://www.msn.com/en-gb/news/example/story-id",
            article_file=article,
            output_dir=root / "out",
            package_id="msn_store_example",
            file_prefix="msn_store_example",
        )
        stored = store_msn_manual_action_total_export_pipeline_result(
            output_dir=root / "report",
            result=result,
            file_prefix="msn_store_example",
        )
        payload = msn_manual_action_total_export_pipeline_store_result_to_json(stored)
        names = {file["file_name"] for file in json.loads(payload)["files"]}
        assert "msn_store_example_report.json" in names
        assert "msn_store_example_manifest.json" in names
        assert str(root) not in payload


if __name__ == "__main__":
    test_pipeline_store_writes_safe_report_and_manifest()
    print("MSN manual action Total Export pipeline store self-test passed.")
