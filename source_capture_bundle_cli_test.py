from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from source_capture_bundle_cli import main


def test_source_capture_bundle_cli() -> None:
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        content_path = root / "content.json"
        comments_path = root / "comments.json"
        output_dir = root / "out"
        content_path.write_text(
            json.dumps(
                {
                    "content_extraction_id": "content.fixture",
                    "adapter_id": "fixture_adapter",
                    "source_url": "https://fixture.test/story",
                    "title": "Fixture title",
                    "body_text": "Fixture body text.",
                }
            ),
            encoding="utf-8",
        )
        comments_path.write_text(
            json.dumps({"comment_extraction_id": "comments.fixture", "comment_count": 1}),
            encoding="utf-8",
        )
        exit_code = main(
            [
                "--content-extraction-json",
                str(content_path),
                "--comment-extraction-json",
                str(comments_path),
                "--output-dir",
                str(output_dir),
                "--operator-note",
                "cli fixture",
            ]
        )
        assert exit_code == 0
        assert len(list(output_dir.glob("*.json"))) == 4


if __name__ == "__main__":
    test_source_capture_bundle_cli()
    print("Source capture bundle CLI self-test passed.")
