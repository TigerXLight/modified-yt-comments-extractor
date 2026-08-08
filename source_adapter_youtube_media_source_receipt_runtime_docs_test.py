from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_YOUTUBE_MEDIA_SOURCE_RECEIPT_RUNTIME.md").read_text(encoding="utf-8")
    assert "YouTube Media Source Receipt" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "youtube_media_source_receipt" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter YouTube Media Source Receipt Runtime docs self-test passed.")
