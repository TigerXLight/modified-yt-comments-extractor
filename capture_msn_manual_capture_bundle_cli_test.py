from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_cli_builds_bundle_from_explicit_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        article = root / "article.txt"
        comments = root / "comments.json"
        out = root / "out"
        article.write_text("Article title\nThis is the article body copied from an approved operator artifact.", encoding="utf-8")
        comments.write_text(json.dumps([{"author": "Alice", "text": "Visible comment one"}]), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                "capture_msn_manual_capture_bundle_cli.py",
                "--source-url",
                "https://www.msn.com/en-gb/news/example/story-id",
                "--article-file",
                str(article),
                "--comments-file",
                str(comments),
                "--output-dir",
                str(out),
                "--file-prefix",
                "manual_msn_bundle",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert completed.returncode == 0, completed.stderr
        payload = json.loads(completed.stdout)
        assert payload["bundle"]["comment_count"] == 1
        assert payload["bundle"]["ready_for_total_export_review"] is True
        assert "manual_msn_bundle.json" in {file["file_name"] for file in payload["store_result"]["files"]}
        assert str(root) not in completed.stdout


if __name__ == "__main__":
    test_cli_builds_bundle_from_explicit_artifacts()
    print("MSN manual capture bundle CLI self-test passed.")
