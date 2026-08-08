from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_SOURCE_CLAIM_REVIEW_CLOSEOUT_RUNTIME.md").read_text(encoding="utf-8")
    assert "Source Claim Review Closeout" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "source_claim_review_closeout" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Source Claim Review Closeout Runtime docs self-test passed.")
