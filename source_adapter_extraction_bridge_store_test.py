from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from source_adapter_extraction_bridge import build_source_adapter_extraction_bridge
from source_adapter_extraction_bridge_store import store_source_adapter_extraction_bridge


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        article = root / "article.html"
        article.write_bytes(b"<html><h1>Store title</h1><article><p>Store body.</p></article></html>")
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
                    ],
                }
            ],
        }
        package = build_source_adapter_extraction_bridge(intake, [{"artifact_basename": article.name, "path": str(article)}])
        stored = store_source_adapter_extraction_bridge(package, root / "out")
        assert stored["store_status"] == "STORED"
        assert stored["output_file_count"] == 5
        assert stored["verification"]["verified"] is True


if __name__ == "__main__":
    main()
    print("Source Adapter Extraction Bridge store self-test passed.")
