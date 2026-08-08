from pathlib import Path

doc = Path("SOURCE_ADAPTER_CREDENTIAL_REFERENCE_AUDIT_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Credential Reference Audit Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_CREDENTIAL_REFERENCE_AUDIT_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_CREDENTIAL_REFERENCE_AUDIT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Credential Reference Audit Runtime docs self-test passed.")
