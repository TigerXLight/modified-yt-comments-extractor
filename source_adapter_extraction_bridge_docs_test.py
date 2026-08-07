from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_EXTRACTION_BRIDGE.md").read_text(encoding="utf-8")
    required = [
        "Adapter Extraction Bridge",
        "source_adapter_artifact_intake",
        "shared content/comment extraction",
        "does not fetch URLs",
        "does not scan folders",
        "READY_FOR_SHARED_CAPTURE_BUNDLE",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing


if __name__ == "__main__":
    main()
    print("Source Adapter Extraction Bridge docs self-test passed.")
