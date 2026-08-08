from source_adapter_final_roadmap_acceptance_runtime import example_source_adapter_final_roadmap_acceptance_runtime_package
from source_adapter_final_roadmap_acceptance_runtime_verifier import verify_source_adapter_final_roadmap_acceptance_runtime

package = example_source_adapter_final_roadmap_acceptance_runtime_package()
verified = verify_source_adapter_final_roadmap_acceptance_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_final_roadmap_acceptance_runtime(broken)["verified"]
print("Source Adapter Final Roadmap Acceptance Runtime verifier self-test passed.")
