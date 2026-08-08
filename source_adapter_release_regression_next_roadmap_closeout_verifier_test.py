from source_adapter_release_regression_next_roadmap_closeout import example_release_regression_next_roadmap_closeout_package
from source_adapter_release_regression_next_roadmap_closeout_verifier import verify_source_adapter_release_regression_next_roadmap_closeout


def main() -> None:
    result = verify_source_adapter_release_regression_next_roadmap_closeout(example_release_regression_next_roadmap_closeout_package())
    assert result["verified"] is True
    assert result["issue_count"] == 0
    assert result["release_note_section_count"] >= 1
    print("Source Adapter Release Regression Next Roadmap Closeout verifier self-test passed.")


if __name__ == "__main__":
    main()
