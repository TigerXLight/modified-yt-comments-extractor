from __future__ import annotations

from copy import deepcopy

from source_adapter_operator_approved_execution_runtime import build_source_adapter_operator_approved_execution_runtime
from source_adapter_operator_approved_execution_runtime_verifier import verify_source_adapter_operator_approved_execution_runtime


def main() -> None:
    package = build_source_adapter_operator_approved_execution_runtime().as_dict()
    result = verify_source_adapter_operator_approved_execution_runtime(package)
    assert result["verified"] is True
    assert result["issue_count"] == 0
    assert result["approval_packet_row_count"] == 5
    assert result["execution_queue_row_count"] == 5
    assert result["executed_row_count"] == 5
    assert result["provider_receipt_row_count"] == 25
    bad = deepcopy(package)
    bad["source_adapter_provider_execution_receipt_batch"]["provider_execution_receipt_rows"][0]["raw_credential"] = "not allowed"
    bad_result = verify_source_adapter_operator_approved_execution_runtime(bad)
    assert bad_result["verified"] is False
    assert any(issue["issue_id"] == "secret_like_material_present" for issue in bad_result["issues"])
    print("Source Adapter Operator Approved Execution Runtime verifier self-test passed.")


if __name__ == "__main__":
    main()
