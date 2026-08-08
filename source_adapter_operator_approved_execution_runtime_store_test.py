from __future__ import annotations

import tempfile
from pathlib import Path

from source_adapter_operator_approved_execution_runtime import (
    STATUS,
    build_source_adapter_operator_approved_execution_runtime,
)
from source_adapter_operator_approved_execution_runtime_store import (
    STORE_SCHEMA_VERSION,
    store_source_adapter_operator_approved_execution_runtime,
)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        package = build_source_adapter_operator_approved_execution_runtime(output_dir=tmpdir).as_dict()
        result = store_source_adapter_operator_approved_execution_runtime(package, tmpdir)
        assert result["schema_version"] == STORE_SCHEMA_VERSION
        assert result["store_status"] == "STORED"
        assert result["operator_approved_execution_runtime_status"] == STATUS
        assert result["approval_packet_row_count"] == 5
        assert result["execution_queue_row_count"] == 5
        assert result["executed_row_count"] == 5
        assert result["provider_receipt_row_count"] == 25
        assert result["credential_reference_ledger_row_count"] == 5
        assert result["output_file_count"] == 8
        assert result["verification"]["verified"] is True
        for stored in result["stored_files"]:
            path = Path(stored["path"])
            assert path.exists(), path
            assert path.stat().st_size == stored["byte_count"]
    print("Source Adapter Operator Approved Execution Runtime store self-test passed.")


if __name__ == "__main__":
    main()
