from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_comment_extraction_cli import run


def test_cli_extracts_and_stores() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "comments.txt").write_text("A: first\n\nB: second", encoding="utf-8")
        out = base / "out"
        result = run(
            [
                "--adapter-id",
                "example",
                "--source-url",
                "https://example.com/story",
                "--artifact",
                "comments_json_or_text=comments.txt",
                "--base-dir",
                str(base),
                "--store",
                "--verify",
                "--out-dir",
                str(out),
            ]
        )
        assert result["store_status"] == "STORED"
        assert result["comment_count"] == 2
        assert len(list(out.glob("*.json"))) == 3


if __name__ == "__main__":
    test_cli_extracts_and_stores()
    print("Source comment extraction CLI self-test passed.")
