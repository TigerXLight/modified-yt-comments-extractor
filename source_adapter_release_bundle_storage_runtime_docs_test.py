from pathlib import Path

doc = Path("SOURCE_ADAPTER_RELEASE_BUNDLE_STORAGE_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Release Bundle Storage Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_RELEASE_BUNDLE_STORAGE_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_RELEASE_BUNDLE_STORAGE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Release Bundle Storage Runtime docs self-test passed.")
