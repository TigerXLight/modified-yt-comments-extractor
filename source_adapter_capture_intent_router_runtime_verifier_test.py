from source_adapter_capture_intent_router_runtime import example_source_adapter_capture_intent_router_runtime_package
from source_adapter_capture_intent_router_runtime_verifier import verify_source_adapter_capture_intent_router_runtime

package = example_source_adapter_capture_intent_router_runtime_package()
verified = verify_source_adapter_capture_intent_router_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_capture_intent_router_runtime(broken)["verified"]
print("Source Adapter Capture Intent Router Runtime verifier self-test passed.")
