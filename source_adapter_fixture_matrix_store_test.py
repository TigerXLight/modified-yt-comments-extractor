from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from source_adapter_fixture_matrix_store import store_source_adapter_fixture_matrix


def test_store_writes_expected_files() -> None:
    specs = [{"adapter_id": "article", "source_kind": "web", "domains": ["article.example"]}]
    with TemporaryDirectory() as tmp:
        result = store_source_adapter_fixture_matrix(specs, tmp)
        assert result["schema_version"] == "source_adapter_fixture_matrix_store_v1"
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 5
        assert result["verification"]["verified"] is True
        for item in result["stored_files"]:
            path = Path(tmp) / item["filename"]
            assert path.exists()
            assert path.stat().st_size == item["byte_count"]


if __name__ == "__main__":
    test_store_writes_expected_files()
    print("Source Adapter Fixture Matrix store self-test passed.")
