from source_adapter_operator_delivery_receipt_closeout import HANDOFF_STATUS, STATUS, example_operator_delivery_receipt_closeout_package
from source_adapter_operator_delivery_receipt_closeout_verifier import verify_source_adapter_operator_delivery_receipt_closeout_package

p = example_operator_delivery_receipt_closeout_package()
assert p["operator_delivery_receipt_closeout_status"] == STATUS
assert p["source_adapter_operator_delivery_receipt_closeout_handoff"]["handoff_status"] == HANDOFF_STATUS
assert p["source_adapter_operator_delivery_receipt_review"]["operator_delivery_receipt_review_row_count"] == 20
assert p["source_adapter_operator_delivery_acceptance_matrix"]["operator_delivery_acceptance_row_count"] == 5
assert p["source_adapter_operator_delivery_release_gate"]["release_section_completion_ready"] is True
v = verify_source_adapter_operator_delivery_receipt_closeout_package(p)
assert v["verified"], v
print("Source Adapter Operator Delivery Receipt Closeout self-test passed.")
