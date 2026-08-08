from source_adapter_archive_result_polling_runtime import HANDOFF_STATUS, ROW_KEY, STATUS, example_source_adapter_archive_result_polling_runtime_package
from source_adapter_archive_result_polling_runtime_verifier import verify_source_adapter_archive_result_polling_runtime_package

package = example_source_adapter_archive_result_polling_runtime_package()
assert package["status"] == STATUS, package
assert package["handoff"]["handoff_status"] == HANDOFF_STATUS, package["handoff"]
assert package["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS", package["operator_summary"]
assert package[f"{ROW_KEY}_row_count"] == 25, package
assert len(package[ROW_KEY]) == 25, package[ROW_KEY]
assert all(not row["credential_secret_material_present"] for row in package[ROW_KEY])
assert all(row["receipt_required"] for row in package[ROW_KEY])
verification = verify_source_adapter_archive_result_polling_runtime_package(package)
assert verification["verified"], verification
print("Source Adapter Archive Result Polling Runtime self-test passed.")
