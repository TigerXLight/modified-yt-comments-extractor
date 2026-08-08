from source_adapter_total_export_assembly_runtime import example_source_adapter_total_export_assembly_runtime_package
from source_adapter_total_export_assembly_runtime_verifier import verify_source_adapter_total_export_assembly_runtime

package = example_source_adapter_total_export_assembly_runtime_package()
verified = verify_source_adapter_total_export_assembly_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_total_export_assembly_runtime(broken)["verified"]
print("Source Adapter Total Export Assembly Runtime verifier self-test passed.")
