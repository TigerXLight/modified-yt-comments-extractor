from source_adapter_archive_provider_submission_backend import STATUS, HANDOFF_STATUS, example_archive_provider_submission_backend_package
from source_adapter_archive_provider_submission_backend_verifier import verify_source_adapter_archive_provider_submission_backend_package

p = example_archive_provider_submission_backend_package()
assert p["status"] == STATUS
assert p["handoff"]["handoff_status"] == HANDOFF_STATUS
assert p["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
assert p["archive_submission_row_count"] == 5
assert p["archive_provider_count"] >= 4
v = verify_source_adapter_archive_provider_submission_backend_package(p)
assert v["verified"], v
print("Source Adapter Archive Provider Submission Backend self-test passed.")
