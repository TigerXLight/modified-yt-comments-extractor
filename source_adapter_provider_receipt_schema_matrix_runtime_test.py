from source_adapter_provider_receipt_schema_matrix_runtime import HANDOFF_STATUS, KEYS_ACCOUNTS_LABEL, LOCAL_ASR_PROFILE, ONLINE_ASR_CANDIDATE, ROW_KEY, STATUS, example_source_adapter_provider_receipt_schema_matrix_runtime_package
from source_adapter_provider_receipt_schema_matrix_runtime_verifier import verify_source_adapter_provider_receipt_schema_matrix_runtime

package = example_source_adapter_provider_receipt_schema_matrix_runtime_package()
assert package["status"] == STATUS
assert package["handoff"]["handoff_status"] == HANDOFF_STATUS
assert package["operator_summary"]["keys_accounts_label"] == KEYS_ACCOUNTS_LABEL
assert package["operator_summary"]["local_asr_profile"] == LOCAL_ASR_PROFILE
assert package["operator_summary"]["online_asr_candidate"] == ONLINE_ASR_CANDIDATE
assert package["operator_summary"]["online_asr_adjacent_to_local_asr"] is True
assert package["operator_summary"]["secret_material_present"] is False
assert package["operator_summary"]["implemented_runtime_surface"] is True
assert package["operator_summary"]["operator_approval_required_count"] > 0
assert len(package[ROW_KEY]) == 78
verification = verify_source_adapter_provider_receipt_schema_matrix_runtime(package)
assert verification["verified"], verification
print("Source Adapter Provider Receipt Schema Matrix Runtime self-test passed.")
