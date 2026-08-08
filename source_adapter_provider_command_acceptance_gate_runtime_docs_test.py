from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_PROVIDER_COMMAND_ACCEPTANCE_GATE_RUNTIME.md").read_text(encoding="utf-8")
    assert "Provider Command Acceptance Gate" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "provider_command_acceptance_gate" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Provider Command Acceptance Gate Runtime docs self-test passed.")
