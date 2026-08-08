from source_adapter_gui_keys_accounts_add_provider_panel_runtime import HANDOFF_STATUS, KEYS_ACCOUNTS_LABEL, ROW_KEY, STATUS, example_source_adapter_gui_keys_accounts_add_provider_panel_runtime_package
from source_adapter_gui_keys_accounts_add_provider_panel_runtime_verifier import verify_source_adapter_gui_keys_accounts_add_provider_panel_runtime

package = example_source_adapter_gui_keys_accounts_add_provider_panel_runtime_package()
assert package["status"] == STATUS
assert package["handoff"]["handoff_status"] == HANDOFF_STATUS
assert package["operator_summary"]["keys_accounts_label"] == KEYS_ACCOUNTS_LABEL
assert package["operator_summary"]["secret_material_present"] is False
assert package["operator_summary"]["implemented_runtime_surface"] is True
assert package["operator_summary"]["operator_approval_required_count"] > 0
assert len(package[ROW_KEY]) == 78
verification = verify_source_adapter_gui_keys_accounts_add_provider_panel_runtime(package)
assert verification["verified"], verification
print("Source Adapter GUI KEYS Accounts Add Provider Panel Runtime self-test passed.")
