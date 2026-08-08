from pathlib import Path

doc = Path("SOURCE_ADAPTER_RELEASE_INDEX_PUBLISH_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Release Index Publish Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_RELEASE_INDEX_PUBLISH_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_RELEASE_INDEX_PUBLISH_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Release Index Publish Runtime docs self-test passed.")
