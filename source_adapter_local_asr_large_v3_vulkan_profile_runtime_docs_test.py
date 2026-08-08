from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_LOCAL_ASR_LARGE_V3_VULKAN_PROFILE_RUNTIME.md").read_text(encoding="utf-8")
    assert "Local ASR Large V3 Vulkan Profile" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "local_asr_large_v3_vulkan_profile" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Local ASR Large V3 Vulkan Profile Runtime docs self-test passed.")
