from pathlib import Path


def main() -> None:
    doc = Path("SOURCE_ADAPTER_CAPTURE_BUNDLE_BRIDGE.md").read_text(encoding="utf-8")
    assert "Adapter Capture Bundle Bridge" in doc
    assert "source_capture_bundle" in doc
    assert "Total Export" in doc


if __name__ == "__main__":
    main()
    print("Source Adapter Capture Bundle Bridge docs self-test passed.")
