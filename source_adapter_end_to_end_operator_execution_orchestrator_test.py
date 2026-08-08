from source_adapter_end_to_end_operator_execution_orchestrator import STATUS, HANDOFF_STATUS, example_end_to_end_operator_execution_orchestrator_package
from source_adapter_end_to_end_operator_execution_orchestrator_verifier import verify_source_adapter_end_to_end_operator_execution_orchestrator_package

p = example_end_to_end_operator_execution_orchestrator_package()
assert p["status"] == STATUS
assert p["handoff"]["handoff_status"] == HANDOFF_STATUS
assert p["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
assert p["end_to_end_receipt_row_count"] == 5
assert p["provider_action_receipt_count"] == 25
assert p["delivery_receipt_count"] == 10
v = verify_source_adapter_end_to_end_operator_execution_orchestrator_package(p)
assert v["verified"], v
print("Source Adapter End-to-End Operator Execution Orchestrator self-test passed.")
