from __future__ import annotations

import hashlib
from pathlib import Path

from source_adapter_artifact_intake import build_source_adapter_artifact_intake
from source_adapter_artifact_intake_store import store_source_adapter_artifact_intake


def test_store_writes_expected_files(tmp_path: Path) -> None:
    artifact = tmp_path / "article.html"
    data = b"<html>stored</html>"
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
    package = build_source_adapter_artifact_intake(session, {"r.article": str(artifact)})
    result = store_source_adapter_artifact_intake(package, tmp_path / "out")
    assert result["store_status"] == "STORED"
    assert result["output_file_count"] == 5
    assert result["verification"]["verified"] is True
    for stored in result["stored_files"]:
        assert (tmp_path / "out" / stored["filename"]).is_file()


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_store_writes_expected_files(Path(tmp))
    print("Source Adapter Artifact Intake store self-test passed.")
