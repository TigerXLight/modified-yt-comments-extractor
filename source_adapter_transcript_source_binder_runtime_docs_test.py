from pathlib import Path

doc = Path("SOURCE_ADAPTER_TRANSCRIPT_SOURCE_BINDER_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Transcript Source Binder Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_TRANSCRIPT_SOURCE_BINDER_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_TRANSCRIPT_SOURCE_BINDER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Transcript Source Binder Runtime docs self-test passed.")
