from tempfile import TemporaryDirectory

from source_adapter_next_roadmap_section_selection_closeout import example_next_roadmap_section_selection_closeout_package
from source_adapter_next_roadmap_section_selection_closeout_store import store_source_adapter_next_roadmap_section_selection_closeout


def main() -> None:
    with TemporaryDirectory() as tmp:
        result = store_source_adapter_next_roadmap_section_selection_closeout(example_next_roadmap_section_selection_closeout_package(), tmp)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 7
        assert result["verification"]["verified"] is True
    print("Source Adapter Next Roadmap Section Selection Closeout store self-test passed.")


if __name__ == "__main__":
    main()
