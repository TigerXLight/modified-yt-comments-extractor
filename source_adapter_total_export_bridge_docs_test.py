from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_TOTAL_EXPORT_BRIDGE.md").read_text(encoding="utf-8")
    assert "source_total_export_package" in text
    assert "Evidence Queue handoff" in text
    assert "planning-only placeholder" in text


if __name__ == "__main__":
    main()
    print("Source Adapter Total Export Bridge docs self-test passed.")
