from source_adapter_source_artifact_digest_runtime import example_source_adapter_source_artifact_digest_runtime_package
from source_adapter_source_artifact_digest_runtime_verifier import verify_source_adapter_source_artifact_digest_runtime

package = example_source_adapter_source_artifact_digest_runtime_package()
verified = verify_source_adapter_source_artifact_digest_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_source_artifact_digest_runtime(broken)["verified"]
print("Source Adapter Source Artifact Digest Runtime verifier self-test passed.")
