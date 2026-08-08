from __future__ import annotations

from tempfile import TemporaryDirectory

from source_adapter_regression_queue_runtime_wiring import example_regression_queue_runtime_wiring_package
from source_adapter_regression_queue_runtime_wiring_store import store_source_adapter_regression_queue_runtime_wiring


def main() -> None:
    with TemporaryDirectory() as tmp:
        result = store_source_adapter_regression_queue_runtime_wiring(example_regression_queue_runtime_wiring_package(), tmp)
    assert result["store_status"] == "STORED"
    assert result["output_file_count"] == 8
    assert result["verification"]["verified"] is True
    assert result["local_runner_queue_row_count"] == 20
    assert result["expanded_binding_row_count"] == 20
    assert result["call_site_wiring_row_count"] >= 4
    assert result["acceptance_receipt_row_count"] == 20
    assert result["named_site_smoke_gate_row_count"] == 5
    print("Source Adapter Regression Queue Runtime Wiring store self-test passed.")


if __name__ == "__main__":
    main()
