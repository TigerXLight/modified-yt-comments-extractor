from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_OPERATOR_RECEIPT_ACCEPTANCE_GATE_RUNTIME.md").read_text(encoding="utf-8")
    assert "Operator Receipt Acceptance Gate" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "operator_receipt_acceptance_gate" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Operator Receipt Acceptance Gate Runtime docs self-test passed.")
