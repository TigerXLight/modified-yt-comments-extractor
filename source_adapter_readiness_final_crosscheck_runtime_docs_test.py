from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_READINESS_FINAL_CROSSCHECK_RUNTIME.md").read_text(encoding="utf-8")
    assert "Readiness Final Crosscheck" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "readiness_final_crosscheck" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Readiness Final Crosscheck Runtime docs self-test passed.")
