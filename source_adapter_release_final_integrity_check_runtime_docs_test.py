from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_RELEASE_FINAL_INTEGRITY_CHECK_RUNTIME.md").read_text(encoding="utf-8")
    assert "Release Final Integrity Check" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "release_final_integrity_check" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Release Final Integrity Check Runtime docs self-test passed.")
