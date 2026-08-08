import tempfile
from pathlib import Path

from source_adapter_priority_site_pack_execution_closeout import example_priority_site_pack_execution_closeout_package
from source_adapter_priority_site_pack_execution_closeout_store import store_source_adapter_priority_site_pack_execution_closeout


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        result = store_source_adapter_priority_site_pack_execution_closeout(example_priority_site_pack_execution_closeout_package(), temp_dir)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 5
        assert result["verification"]["verified"] is True
        for row in result["stored_files"]:
            path = Path(temp_dir) / row["filename"]
            assert path.exists()
            assert path.stat().st_size == row["byte_count"]
    print("Source Adapter Priority Site Pack Execution Closeout store self-test passed.")


if __name__ == "__main__":
    main()
