from __future__ import annotations

from tempfile import TemporaryDirectory

from source_adapter_release_index_bridge import build_source_adapter_release_index_bridge
from source_adapter_release_index_bridge_store import store_source_adapter_release_index_bridge
from source_adapter_release_index_bridge_test import fixture_approved_release_bridge


def main() -> None:
    package = build_source_adapter_release_index_bridge(fixture_approved_release_bridge())
    with TemporaryDirectory() as tmp:
        result = store_source_adapter_release_index_bridge(package, tmp)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 5
        assert result["verification"]["verified"] is True
        assert {entry["role"] for entry in result["stored_files"]} == {
            "source_adapter_release_index_bridge_package",
            "source_adapter_release_index_output_batch",
            "source_adapter_release_index_batch",
            "source_adapter_release_audit_batch_handoff",
            "source_adapter_release_index_bridge_operator_summary",
        }


if __name__ == "__main__":
    main()
    print("Source Adapter Release Index Bridge store self-test passed.")
