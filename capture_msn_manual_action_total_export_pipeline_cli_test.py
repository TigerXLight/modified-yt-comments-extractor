from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_cli_runs_pipeline_and_writes_operator_kit_and_total_export_package() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        article = root / "article.html"
        comments = root / "comments.json"
        out = root / "out"
        article.write_text(
            "<html><head><title>CLI title</title></head><body><h1>CLI title</h1><p>Article body text copied by the operator for Total Export review.</p></body></html>",
            encoding="utf-8",
        )
        comments.write_text(json.dumps({"comments": [{"author": "Reader", "text": "CLI visible comment"}]}), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                "capture_msn_manual_action_total_export_pipeline_cli.py",
                "--source-url",
                "https://www.msn.com/en-gb/news/example/story-id",
                "--article-file",
                str(article),
                "--comments-file",
                str(comments),
                "--output-dir",
                str(out),
                "--package-id",
                "msn_cli_pipeline",
                "--file-prefix",
                "msn_cli_pipeline",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
        payload = json.loads(completed.stdout)
        assert payload["pipeline_result"]["pipeline_implemented"] is True
        assert payload["pipeline_verifier"]["ready_for_total_export_review"] is True
        assert (out / "operator_action_kits" / "msn_cli_pipeline_article_run_approved_action.cmd").is_file()
        assert (out / "total_export_package" / "metadata" / "msn_cli_pipeline_manifest.json").is_file()
        assert str(root) not in completed.stdout


if __name__ == "__main__":
    test_cli_runs_pipeline_and_writes_operator_kit_and_total_export_package()
    print("MSN manual action Total Export pipeline CLI self-test passed.")
