from pathlib import Path

doc = Path("SOURCE_ADAPTER_RELEASE_MANIFEST_SIGNING_RUNTIME.md").read_text(encoding="utf-8")
assert "Source Adapter Release Manifest Signing Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_RELEASE_MANIFEST_SIGNING_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_RELEASE_MANIFEST_SIGNING_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_STAGE" in doc
print("Source Adapter Release Manifest Signing Runtime docs self-test passed.")
