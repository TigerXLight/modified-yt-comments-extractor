from __future__ import annotations

import hashlib
import json
from pathlib import Path

from source_adapter_artifact_intake_cli import main


def test_cli_builds_and_stores(tmp_path: Path) -> None:
    artifact = tmp_path / "article.html"
    data = b"<html>cli</html>"
    artifact.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    session = {
        "source_adapter_capture_session_id": "source_adapter_capture_session.example",
        "artifact_receipts": [
            {
                "receipt_id": "r.article",
                "adapter_id": "article",
                "artifact_role": "article_html_or_text",
                "artifact_basename": "article.html",
                "byte_count": len(data),
                "sha256": digest,
                "source_url": "https://article.example/story",
            }
        ],
    }
    session_path = tmp_path / "session.json"
    bindings_path = tmp_path / "bindings.json"
    out_dir = tmp_path / "out"
    session_path.write_text(json.dumps(session), encoding="utf-8")
    bindings_path.write_text(json.dumps({"r.article": str(artifact)}), encoding="utf-8")
    assert main(["--capture-session-json", str(session_path), "--artifact-files-json", str(bindings_path), "--output-dir", str(out_dir)]) == 0
    assert len(list(out_dir.glob("*.json"))) == 5


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_cli_builds_and_stores(Path(tmp))
    print("Source Adapter Artifact Intake CLI self-test passed.")
