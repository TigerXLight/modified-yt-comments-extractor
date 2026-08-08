from source_adapter_transcript_source_binder_runtime import example_source_adapter_transcript_source_binder_runtime_package
from source_adapter_transcript_source_binder_runtime_verifier import verify_source_adapter_transcript_source_binder_runtime

package = example_source_adapter_transcript_source_binder_runtime_package()
verified = verify_source_adapter_transcript_source_binder_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_transcript_source_binder_runtime(broken)["verified"]
print("Source Adapter Transcript Source Binder Runtime verifier self-test passed.")
