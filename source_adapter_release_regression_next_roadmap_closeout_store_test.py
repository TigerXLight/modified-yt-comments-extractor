from tempfile import TemporaryDirectory

from source_adapter_release_regression_next_roadmap_closeout import example_release_regression_next_roadmap_closeout_package
from source_adapter_release_regression_next_roadmap_closeout_store import store_source_adapter_release_regression_next_roadmap_closeout


def main() -> None:
    with TemporaryDirectory() as tmp:
        result = store_source_adapter_release_regression_next_roadmap_closeout(example_release_regression_next_roadmap_closeout_package(), tmp)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 6
        assert result["verification"]["verified"] is True
    print("Source Adapter Release Regression Next Roadmap Closeout store self-test passed.")


if __name__ == "__main__":
    main()
