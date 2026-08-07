from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_cli_builds_and_stores_collection() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        article = root / "article.html"
        metadata = root / "metadata.json"
        out = root / "out"
        article.write_text("<article>Body</article>", encoding="utf-8")
        metadata.write_text('{"captured":true}', encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "source_artifact_collection_cli.py",
                "--adapter-id",
                "fixture",
                "--source-url",
                "https://fixture.example/story",
                "--artifact",
                f"article_html_or_text={article}",
                "--artifact",
                f"metadata_json={metadata}",
                "--output-dir",
                str(out),
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        receipt = json.loads(result.stdout)
        assert receipt["store_status"] == "STORED"
        assert receipt["verification"]["verified"] is True
        assert len(receipt["stored_files"]) == 3


def main() -> None:
    test_cli_builds_and_stores_collection()
    print("Source artifact collection CLI self-test passed.")


if __name__ == "__main__":
    main()
