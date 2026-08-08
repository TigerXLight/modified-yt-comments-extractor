from source_adapter_operator_handoff_packet_runtime import example_source_adapter_operator_handoff_packet_runtime_package
from source_adapter_operator_handoff_packet_runtime_verifier import verify_source_adapter_operator_handoff_packet_runtime

package = example_source_adapter_operator_handoff_packet_runtime_package()
verified = verify_source_adapter_operator_handoff_packet_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_operator_handoff_packet_runtime(broken)["verified"]
print("Source Adapter Operator Handoff Packet Runtime verifier self-test passed.")
