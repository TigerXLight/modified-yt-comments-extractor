from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_ASR_SOURCE_TRACEABILITY_RECEIPT_RUNTIME.md").read_text(encoding="utf-8")
    assert "ASR Source Traceability Receipt" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "asr_source_traceability_receipt" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter ASR Source Traceability Receipt Runtime docs self-test passed.")
