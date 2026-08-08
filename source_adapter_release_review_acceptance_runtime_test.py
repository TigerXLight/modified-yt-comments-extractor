from source_adapter_release_review_acceptance_runtime import STATUS, HANDOFF_STATUS, example_source_adapter_release_review_acceptance_runtime_package
from source_adapter_release_review_acceptance_runtime_verifier import verify_source_adapter_release_review_acceptance_runtime_package

p = example_source_adapter_release_review_acceptance_runtime_package()
assert p["status"] == STATUS
assert p["handoff"]["handoff_status"] == HANDOFF_STATUS
assert p["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
assert p["release_review_acceptance_row_count"] == 5
v = verify_source_adapter_release_review_acceptance_runtime_package(p)
assert v["verified"], v
print("Source Adapter Release Review Acceptance Runtime self-test passed.")
