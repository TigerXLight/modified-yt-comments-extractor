from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_ONLINE_ASR_VISUAL_PARITY_GUARD_RUNTIME.md").read_text(encoding="utf-8")
    assert "Online ASR Visual Parity Guard" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "online_asr_visual_parity_guard" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Online ASR Visual Parity Guard Runtime docs self-test passed.")
