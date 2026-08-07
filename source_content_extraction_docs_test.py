from pathlib import Path


def test_docs_capture_required_boundaries() -> None:
    text = Path("SOURCE_CONTENT_EXTRACTION.md").read_text(encoding="utf-8")
    required = [
        "adapter-neutral content extraction",
        "explicit operator-supplied artifacts",
        "does not fetch URLs",
        "does not launch browsers",
        "Future source adapters",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing


if __name__ == "__main__":
    test_docs_capture_required_boundaries()
    print("Source content extraction docs self-test passed.")
