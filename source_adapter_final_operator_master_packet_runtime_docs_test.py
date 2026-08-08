from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_FINAL_OPERATOR_MASTER_PACKET_RUNTIME.md").read_text(encoding="utf-8")
    assert "Final Operator Master Packet" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "final_operator_master_packet" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Final Operator Master Packet Runtime docs self-test passed.")
