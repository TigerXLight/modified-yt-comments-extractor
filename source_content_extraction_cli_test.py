import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def test_cli_writes_store_output() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        artifact = root / "article.txt"
        artifact.write_text("CLI title\nCLI body.", encoding="utf-8")
        out = root / "out"
        completed = subprocess.run(
            [
                sys.executable,
                "source_content_extraction_cli.py",
                "--adapter-id",
                "cli_adapter",
                "--source-url",
                "https://cli.example/story",
                "--artifact",
                f"article_text={artifact}",
                "--output-dir",
                str(out),
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        assert payload["store_status"] == "STORED"
        assert payload["verification"]["verified"] is True
        assert len(list(out.glob("*.json"))) == 3


if __name__ == "__main__":
    test_cli_writes_store_output()
    print("Source content extraction CLI self-test passed.")
