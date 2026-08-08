from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_ONLINE_ASR_RECEIPT_IMPORT_BRIDGE_RUNTIME.md").read_text(encoding="utf-8")
    assert "Online ASR Receipt Import Bridge" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "online_asr_receipt_import_bridge" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Online ASR Receipt Import Bridge Runtime docs self-test passed.")
