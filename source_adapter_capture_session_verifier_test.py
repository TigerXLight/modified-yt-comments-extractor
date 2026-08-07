from __future__ import annotations

from source_adapter_capture_session import build_source_adapter_capture_session
from source_adapter_capture_session_verifier import verify_source_adapter_capture_session


def _package() -> dict:
    return build_source_adapter_capture_session(
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


def test_verifier_accepts_valid_package() -> None:
    result = verify_source_adapter_capture_session(_package())
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_verifier_rejects_bad_hash() -> None:
    package = _package()
    package["artifact_receipts"][0]["sha256"] = "bad"
    result = verify_source_adapter_capture_session(package)
    assert result["verified"] is False
    assert result["issue_count"] >= 1


if __name__ == "__main__":
    test_verifier_accepts_valid_package()
    test_verifier_rejects_bad_hash()
    print("Source Adapter Capture Session verifier self-test passed.")
