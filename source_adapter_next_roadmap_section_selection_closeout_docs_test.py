from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_NEXT_ROADMAP_SECTION_SELECTION_CLOSEOUT.md").read_text(encoding="utf-8")
    required = [
        "Source Adapter Next Roadmap Section Selection Closeout",
        "source_adapter_next_roadmap_section_selection_closeout_v1",
        "Codex prompt queue",
        "regression command groups",
        "KEYS/ACCOUNTS",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing
    print("Source Adapter Next Roadmap Section Selection Closeout docs self-test passed.")


if __name__ == "__main__":
    main()
