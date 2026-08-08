from pathlib import Path

doc = Path("SOURCE_ADAPTER_SECRET_SCOPE_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Secret Scope Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_SECRET_SCOPE_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_SECRET_SCOPE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Secret Scope Runtime docs self-test passed.")
