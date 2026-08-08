from pathlib import Path

doc = Path("SOURCE_ADAPTER_SHADOW_ROOT_EXTRACTION_PLAN_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Shadow Root Extraction Plan Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_SHADOW_ROOT_EXTRACTION_PLAN_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_SHADOW_ROOT_EXTRACTION_PLAN_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Shadow Root Extraction Plan Runtime docs self-test passed.")
