from pathlib import Path

doc = Path("SOURCE_ADAPTER_PROVIDER_HEALTH_REVIEW_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Provider Health Review Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_PROVIDER_HEALTH_REVIEW_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_PROVIDER_HEALTH_REVIEW_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Provider Health Review Runtime docs self-test passed.")
