from pathlib import Path


def test_docs_cover_safety_and_inputs():
    text = Path("SOURCE_ADAPTER_REGISTRY_UPDATE.md").read_text(encoding="utf-8")
    assert "Adapter Registry Update" in text
    assert "adapter registry handoff" in text
    assert "does not mutate" in text
    assert "does not fetch URLs" in text
    assert "shared-stage" in text


if __name__ == "__main__":
    test_docs_cover_safety_and_inputs()
    print("Source Adapter Registry Update docs self-test passed.")
