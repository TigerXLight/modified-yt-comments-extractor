from pathlib import Path
from tempfile import TemporaryDirectory

from source_adapter_next_roadmap_section_selection_closeout_cli import main as cli_main


def main() -> None:
    with TemporaryDirectory() as tmp:
        assert cli_main(["--output-dir", tmp, "--section", "regular_regression_promotion", "--section", "documentation_handoff_refresh"]) == 0
        assert len(list(Path(tmp).glob("*.json"))) == 7
    print("Source Adapter Next Roadmap Section Selection Closeout CLI self-test passed.")


if __name__ == "__main__":
    main()
