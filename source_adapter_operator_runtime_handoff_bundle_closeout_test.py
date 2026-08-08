from source_adapter_operator_runtime_handoff_bundle_closeout import HANDOFF_STATUS, KEYS_ACCOUNTS_LABEL, ROW_KEY, STATUS, example_source_adapter_operator_runtime_handoff_bundle_closeout_package
from source_adapter_operator_runtime_handoff_bundle_closeout_verifier import verify_source_adapter_operator_runtime_handoff_bundle_closeout

package = example_source_adapter_operator_runtime_handoff_bundle_closeout_package()
assert package["status"] == STATUS
assert package["handoff"]["handoff_status"] == HANDOFF_STATUS
assert package["operator_summary"]["keys_accounts_label"] == KEYS_ACCOUNTS_LABEL
assert package["operator_summary"]["secret_material_present"] is False
assert package["operator_summary"]["implemented_runtime_surface"] is True
assert len(package[ROW_KEY]) == 25
verification = verify_source_adapter_operator_runtime_handoff_bundle_closeout(package)
assert verification["verified"], verification
print("Source Adapter Operator Runtime Handoff Bundle Closeout self-test passed.")
