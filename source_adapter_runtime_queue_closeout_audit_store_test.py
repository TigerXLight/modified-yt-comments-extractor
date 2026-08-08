from __future__ import annotations

from tempfile import TemporaryDirectory

from source_adapter_runtime_queue_closeout_audit import example_runtime_queue_closeout_audit_package
from source_adapter_runtime_queue_closeout_audit_store import store_source_adapter_runtime_queue_closeout_audit


def main() -> None:
    with TemporaryDirectory() as tmp:
        result = store_source_adapter_runtime_queue_closeout_audit(example_runtime_queue_closeout_audit_package(), tmp)
    assert result["store_status"] == "STORED"
    assert result["output_file_count"] == 6
    assert result["verification"]["verified"] is True
    assert result["coverage_row_count"] >= 6
    assert result["local_runner_queue_row_count"] == 20
    assert result["expanded_binding_row_count"] == 20
    assert result["acceptance_receipt_row_count"] == 20
    assert result["named_site_smoke_gate_row_count"] == 5
    print("Source Adapter Runtime Queue Closeout Audit store self-test passed.")


if __name__ == "__main__":
    main()
