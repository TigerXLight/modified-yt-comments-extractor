from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_msn_manual_action_total_export_pipeline import (
    build_msn_manual_action_total_export_pipeline,
    msn_manual_action_total_export_pipeline_result_to_json,
)


def test_pipeline_generates_action_kits_and_total_export_package() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        article = root / "article.html"
        comments = root / "comments.json"
        out = root / "out"
        article.write_text(
            "<html><head><title>MSN Test</title></head><body><h1>MSN Test</h1><p>Article body copied by the operator for review.</p></body></html>",
            encoding="utf-8",
        )
        comments.write_text(json.dumps({"comments": [{"author": "Reader", "text": "Visible comment from saved artifact"}]}), encoding="utf-8")
        result = build_msn_manual_action_total_export_pipeline(
            source_url="https://www.msn.com/en-gb/news/example/story-id",
            article_file=article,
            comments_file=comments,
            output_dir=out,
            package_id="msn_pipeline_example",
            file_prefix="msn_pipeline_example",
        )
        assert result.pipeline_implemented is True
        assert result.generated_operator_action_kits is True
        assert result.action_kit_file_count >= 8
        assert result.total_export_file_count >= 5
        assert result.comment_count == 1
        assert (out / "operator_action_kits" / "msn_pipeline_example_article_run_approved_action.cmd").is_file()
        assert (out / "operator_action_kits" / "msn_pipeline_example_comments_msn_comments_shadow_root_snippet.js").is_file()
        assert (out / "total_export_package" / "page_capture" / "msn_pipeline_example_article_text.txt").is_file()
        payload = msn_manual_action_total_export_pipeline_result_to_json(result)
        assert str(root) not in payload
        assert "full_local_path_serialized" in payload
        assert json.loads(payload)["total_export_verification_report"]["ready_for_total_export_review"] is True


if __name__ == "__main__":
    test_pipeline_generates_action_kits_and_total_export_package()
    print("MSN manual action Total Export pipeline self-test passed.")
