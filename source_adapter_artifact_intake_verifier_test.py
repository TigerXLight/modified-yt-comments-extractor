from __future__ import annotations

import hashlib
from pathlib import Path

from source_adapter_artifact_intake import build_source_adapter_artifact_intake
from source_adapter_artifact_intake_verifier import verify_source_adapter_artifact_intake


def test_verifier_accepts_valid_package(tmp_path: Path) -> None:
    artifact = tmp_path / "article.html"
    data = b"<html>verify</html>"
    artifact.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    package = build_source_adapter_artifact_intake(
        {
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
        },
        {"r.article": str(artifact)},
    )
    result = verify_source_adapter_artifact_intake(package)
    assert result["verified"] is True
    assert result["issue_count"] == 0


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_verifier_accepts_valid_package(Path(tmp))
    print("Source Adapter Artifact Intake verifier self-test passed.")
