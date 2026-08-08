from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_TRANSCRIPT_ASR_RECEIPT_FINALIZER_RUNTIME.md").read_text(encoding="utf-8")
    assert "Transcript ASR Receipt Finalizer" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "transcript_asr_receipt_finalizer" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Transcript ASR Receipt Finalizer Runtime docs self-test passed.")
