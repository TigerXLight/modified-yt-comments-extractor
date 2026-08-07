from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        article = root / "article.html"
        article.write_bytes(b"<html><h1>CLI title</h1><article><p>CLI body.</p></article></html>")
        comments = root / "comments.json"
        comments.write_bytes(b'[{"id":"c1","author":"Reader","text":"CLI comment"}]')
        intake = {
            "artifact_intake_status": "ARTIFACT_FILES_VALIDATED",
            "source_adapter_artifact_intake_id": "source_adapter_artifact_intake.example",
            "source_artifact_collection_handoff": {"handoff_status": "READY_FOR_SHARED_EXTRACTION"},
            "source_artifact_collections": [
                {
                    "collection_id": "source_artifacts.example",
                    "adapter_id": "article",
                    "source_url": "https://article.example/story",
                    "collection_status": "READY_FOR_EXTRACTION",
                    "artifacts": [
                        {"role": "article_html_or_text", "filename": article.name, "byte_count": article.stat().st_size, "sha256": hashlib.sha256(article.read_bytes()).hexdigest(), "content_kind": "text"},
                        {"role": "comments_json_or_text", "filename": comments.name, "byte_count": comments.stat().st_size, "sha256": hashlib.sha256(comments.read_bytes()).hexdigest(), "content_kind": "text"},
                    ],
                }
            ],
        }
        bindings = [
            {"adapter_id": "article", "artifact_role": "article_html_or_text", "artifact_basename": article.name, "path": str(article)},
            {"adapter_id": "article", "artifact_role": "comments_json_or_text", "artifact_basename": comments.name, "path": str(comments)},
        ]
        intake_path = root / "intake.json"
        bindings_path = root / "bindings.json"
        intake_path.write_text(json.dumps(intake), encoding="utf-8")
        bindings_path.write_text(json.dumps(bindings), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                "source_adapter_extraction_bridge_cli.py",
                "--artifact-intake-json",
                str(intake_path),
                "--artifact-files-json",
                str(bindings_path),
                "--output-dir",
                str(root / "out"),
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        result = json.loads(proc.stdout)
        assert result["store_status"] == "STORED"
        assert result["verification"]["verified"] is True


if __name__ == "__main__":
    main()
    print("Source Adapter Extraction Bridge CLI self-test passed.")
