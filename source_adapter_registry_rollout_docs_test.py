from pathlib import Path


def test_registry_rollout_docs_cover_safety_and_outputs():
    text = Path("SOURCE_ADAPTER_REGISTRY_ROLLOUT.md").read_text(encoding="utf-8")
    assert "Adapter Registry Rollout" in text
    assert "does not mutate app files" in text
    assert "source selection" in text
    assert "manual or live actions" in text


if __name__ == "__main__":
    test_registry_rollout_docs_cover_safety_and_outputs()
    print("Source Adapter Registry Rollout docs self-test passed.")
