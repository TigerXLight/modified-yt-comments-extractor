from source_adapter_keys_accounts_credential_reference_runtime import STATUS, HANDOFF_STATUS, example_keys_accounts_credential_reference_runtime_package
from source_adapter_keys_accounts_credential_reference_runtime_verifier import verify_source_adapter_keys_accounts_credential_reference_runtime_package

p = example_keys_accounts_credential_reference_runtime_package()
assert p["status"] == STATUS
assert p["handoff"]["handoff_status"] == HANDOFF_STATUS
assert p["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
assert p["credential_reference_row_count"] == 5
assert not p["handoff"]["secret_material_returned"]
v = verify_source_adapter_keys_accounts_credential_reference_runtime_package(p)
assert v["verified"], v
print("Source Adapter KEYS/ACCOUNTS Credential Reference Runtime self-test passed.")
