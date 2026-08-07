from __future__ import annotations

import tempfile

from source_adapter_capture_session import build_source_adapter_capture_session
from source_adapter_capture_session_store import store_source_adapter_capture_session


def test_store_writes_five_files() -> None:
    package = build_source_adapter_capture_session(
        {
            "adapters": [{"adapter_id": "article", "artifact_roles": ["article_html_or_text"]}],
            "artifact_intake_templates": {"templates": [{"adapter_id": "article", "artifact_role": "article_html_or_text"}]},
        },
        [
            {
                "adapter_id": "article",
                "artifact_role": "article_html_or_text",
                "artifact_basename": "article.html",
                "byte_count": 12,
                "sha256": "a" * 64,
            }
        ],
    )
    with tempfile.TemporaryDirectory() as tmp:
        result = store_source_adapter_capture_session(package, tmp)
    assert result["store_status"] == "STORED"
    assert result["output_file_count"] == 5
    assert result["verification"]["verified"] is True
    assert all(row["byte_count"] > 0 and len(row["sha256"]) == 64 for row in result["stored_files"])


if __name__ == "__main__":
    test_store_writes_five_files()
    print("Source Adapter Capture Session store self-test passed.")
