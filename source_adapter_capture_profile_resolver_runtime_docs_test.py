from pathlib import Path

doc = Path("SOURCE_ADAPTER_CAPTURE_PROFILE_RESOLVER_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Capture Profile Resolver Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_CAPTURE_PROFILE_RESOLVER_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_CAPTURE_PROFILE_RESOLVER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Capture Profile Resolver Runtime docs self-test passed.")
