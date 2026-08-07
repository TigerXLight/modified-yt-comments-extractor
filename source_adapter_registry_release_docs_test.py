from pathlib import Path


def test_docs_describe_safe_release_boundary():
    doc = Path("SOURCE_ADAPTER_REGISTRY_RELEASE.md").read_text(encoding="utf-8")
    assert "Source Adapter Registry Release" in doc
    assert "does not mutate application registry files" in doc
    assert "does not" in doc
    assert "live/manual actions" in doc


if __name__ == "__main__":
    test_docs_describe_safe_release_boundary()
    print("Source Adapter Registry Release docs self-test passed.")
