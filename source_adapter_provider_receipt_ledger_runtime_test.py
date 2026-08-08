from source_adapter_provider_receipt_ledger_runtime import STATUS, HANDOFF_STATUS, example_source_adapter_provider_receipt_ledger_runtime_package
from source_adapter_provider_receipt_ledger_runtime_verifier import verify_source_adapter_provider_receipt_ledger_runtime_package

p = example_source_adapter_provider_receipt_ledger_runtime_package()
assert p["status"] == STATUS
assert p["handoff"]["handoff_status"] == HANDOFF_STATUS
assert p["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
assert p["provider_receipt_ledger_row_count"] == 25
v = verify_source_adapter_provider_receipt_ledger_runtime_package(p)
assert v["verified"], v
print("Source Adapter Provider Receipt Ledger Runtime self-test passed.")
