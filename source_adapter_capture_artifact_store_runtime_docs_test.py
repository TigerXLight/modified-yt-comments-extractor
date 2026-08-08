from pathlib import Path

doc = Path("SOURCE_ADAPTER_CAPTURE_ARTIFACT_STORE_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Capture Artifact Store Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_CAPTURE_ARTIFACT_STORE_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_CAPTURE_ARTIFACT_STORE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Capture Artifact Store Runtime docs self-test passed.")
