from source_adapter_next_roadmap_section_selection_closeout import HANDOFF_STATUS, example_next_roadmap_section_selection_closeout_package
from source_adapter_next_roadmap_section_selection_closeout_verifier import verify_source_adapter_next_roadmap_section_selection_closeout


def main() -> None:
    result = verify_source_adapter_next_roadmap_section_selection_closeout(example_next_roadmap_section_selection_closeout_package())
    assert result["verified"] is True
    assert result["handoff_status"] == HANDOFF_STATUS
    assert result["selected_section_count"] == 6
    print("Source Adapter Next Roadmap Section Selection Closeout verifier self-test passed.")


if __name__ == "__main__":
    main()
