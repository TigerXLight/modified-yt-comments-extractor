from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_FINAL_CAPTURE_COMMAND_REGISTRY_RUNTIME.md").read_text(encoding="utf-8")
    assert "Final Capture Command Registry" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "final_capture_command_registry" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Final Capture Command Registry Runtime docs self-test passed.")
