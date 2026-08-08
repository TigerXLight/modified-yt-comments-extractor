from source_adapter_archive_closeout_runtime import STATUS, HANDOFF_STATUS, example_source_adapter_archive_closeout_runtime_package
from source_adapter_archive_closeout_runtime_verifier import verify_source_adapter_archive_closeout_runtime_package

p = example_source_adapter_archive_closeout_runtime_package()
assert p["status"] == STATUS, p
assert p["handoff"]["handoff_status"] == HANDOFF_STATUS, p["handoff"]
assert p["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
assert p["issue_count"] == 0, p.get("issues")
assert p["archive_closeout_row_count"] == 5
v = verify_source_adapter_archive_closeout_runtime_package(p)
assert v["verified"], v
print("Source Adapter Archive Closeout Runtime self-test passed.")
