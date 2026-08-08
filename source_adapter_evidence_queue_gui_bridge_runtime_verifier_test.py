from source_adapter_evidence_queue_gui_bridge_runtime import example_source_adapter_evidence_queue_gui_bridge_runtime_package
from source_adapter_evidence_queue_gui_bridge_runtime_verifier import verify_source_adapter_evidence_queue_gui_bridge_runtime

package = example_source_adapter_evidence_queue_gui_bridge_runtime_package()
verified = verify_source_adapter_evidence_queue_gui_bridge_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_evidence_queue_gui_bridge_runtime(broken)["verified"]
print("Source Adapter Evidence Queue GUI Bridge Runtime verifier self-test passed.")
