from source_adapter_comment_shadow_export_ticket_runtime import example_source_adapter_comment_shadow_export_ticket_runtime_package
from source_adapter_comment_shadow_export_ticket_runtime_verifier import verify_source_adapter_comment_shadow_export_ticket_runtime

package = example_source_adapter_comment_shadow_export_ticket_runtime_package()
verified = verify_source_adapter_comment_shadow_export_ticket_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_comment_shadow_export_ticket_runtime(broken)["verified"]
print("Source Adapter Comment Shadow Export Ticket Runtime verifier self-test passed.")
