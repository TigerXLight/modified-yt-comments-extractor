from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path

from source_adapter_fixture_review_cli import main


def test_cli_store_and_verify_json() -> None:
    authoring = {
        "source_adapter_fixture_authoring_id": "source_adapter_fixture_authoring.fixture",
        "template_index": {
            "template_rows": [
                {
                    "adapter_id": "article",
                    "artifact_role": "article_html_or_text",
                    "fixture_type": "saved_article_html_or_text",
                    "operator_supplied_file_required": True,
                    "safe_template_basename": "article.01.saved_article_html_or_text.template.json",
                }
            ]
        },
        "shared_stage_route_plan": {"adapters": [{"adapter_id": "article", "shared_pipeline_stages": ["artifact_collection"]}]},
    }
    authored = {
        "fixtures": [
            {
                "adapter_id": "article",
                "fixture_type": "saved_article_html_or_text",
                "template_safe_basename": "article.01.saved_article_html_or_text.template.json",
                "source_artifact_safe_basename": "article.fixture.html",
                "source_artifact_sha256": "f" * 64,
                "expected_assertions": {},
            }
        ]
    }
    with tempfile.TemporaryDirectory() as tmp:
        authoring_path = Path(tmp) / "authoring.json"
        authored_path = Path(tmp) / "authored.json"
        output_dir = Path(tmp) / "out"
        authoring_path.write_text(json.dumps(authoring), encoding="utf-8")
        authored_path.write_text(json.dumps(authored), encoding="utf-8")
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            assert main([
                "--fixture-authoring-json",
                str(authoring_path),
                "--authored-fixtures-json",
                str(authored_path),
                "--output-dir",
                str(output_dir),
                "--json",
            ]) == 0
        result = json.loads(capture.getvalue())
        assert result["store_status"] == "STORED"
        package_file = next(path for path in output_dir.iterdir() if path.name.endswith("source_adapter_fixture_review_package.json"))
        verify_capture = io.StringIO()
        with contextlib.redirect_stdout(verify_capture):
            assert main(["--verify", str(package_file), "--json"]) == 0
        verified = json.loads(verify_capture.getvalue())
        assert verified["verified"] is True


if __name__ == "__main__":
    test_cli_store_and_verify_json()
    print("Source Adapter Fixture Review CLI self-test passed.")
