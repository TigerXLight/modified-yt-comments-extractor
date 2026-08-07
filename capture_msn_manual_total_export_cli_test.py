from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_cli_builds_written_total_export_package_from_explicit_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        article = root / "article.html"
        comments = root / "comments.json"
        out = root / "out"
        article.write_text("<html><head><title>Example MSN title</title></head><body><h1>Example MSN title</h1><p>Article body paragraph.</p></body></html>", encoding="utf-8")
        comments.write_text(json.dumps({"comments": [{"author": "Reader", "text": "A visible comment"}]}), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                "capture_msn_manual_total_export_cli.py",
                "--source-url",
                "https://www.msn.com/en-gb/news/example/story-id",
                "--article-file",
                str(article),
                "--comments-file",
                str(comments),
                "--output-dir",
                str(out),
                "--package-id",
                "msn_cli_package",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert completed.returncode == 0, completed.stderr
        payload = json.loads(completed.stdout)
        assert payload["packet"]["total_export_manifest_implemented"] is True
        assert payload["packet"]["comment_count"] == 1
        assert "metadata/msn_cli_package_manifest.json" in {file["file_name"] for file in payload["store_result"]["files"]}
        assert (out / "page_capture" / "msn_cli_package_article_text.txt").is_file()
        assert str(root) not in completed.stdout


if __name__ == "__main__":
    test_cli_builds_written_total_export_package_from_explicit_artifacts()
    print("MSN manual Total Export CLI self-test passed.")
