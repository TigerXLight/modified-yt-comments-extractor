from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_EVIDENCE_ITEM_RELEASE_COMMIT_RUNTIME.md").read_text(encoding="utf-8")
    assert "Evidence Item Release Commit" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "evidence_item_release_commit" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Evidence Item Release Commit Runtime docs self-test passed.")
