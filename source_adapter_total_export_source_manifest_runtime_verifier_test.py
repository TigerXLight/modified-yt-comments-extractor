from source_adapter_total_export_source_manifest_runtime import example_source_adapter_total_export_source_manifest_runtime_package
from source_adapter_total_export_source_manifest_runtime_verifier import verify_source_adapter_total_export_source_manifest_runtime

package = example_source_adapter_total_export_source_manifest_runtime_package()
verified = verify_source_adapter_total_export_source_manifest_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_total_export_source_manifest_runtime(broken)["verified"]
print("Source Adapter Total Export Source Manifest Runtime verifier self-test passed.")
