from pathlib import Path

doc = Path("SOURCE_ADAPTER_MANUAL_SMOKE_IMPORT_CLOSEOUT_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Manual Smoke Import Closeout Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_MANUAL_SMOKE_IMPORT_CLOSEOUT_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_MANUAL_SMOKE_IMPORT_CLOSEOUT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Manual Smoke Import Closeout Runtime docs self-test passed.")
