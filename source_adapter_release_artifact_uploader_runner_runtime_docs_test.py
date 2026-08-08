from pathlib import Path

doc = Path("SOURCE_ADAPTER_RELEASE_ARTIFACT_UPLOADER_RUNNER_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Release Artifact Uploader Runner Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_RELEASE_ARTIFACT_UPLOADER_RUNNER_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_RELEASE_ARTIFACT_UPLOADER_RUNNER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Release Artifact Uploader Runner Runtime docs self-test passed.")
