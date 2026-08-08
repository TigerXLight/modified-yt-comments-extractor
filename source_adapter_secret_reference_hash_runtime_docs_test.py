from pathlib import Path

doc = Path("SOURCE_ADAPTER_SECRET_REFERENCE_HASH_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Secret Reference Hash Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_SECRET_REFERENCE_HASH_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_SECRET_REFERENCE_HASH_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Secret Reference Hash Runtime docs self-test passed.")
