from pathlib import Path

doc = Path("SOURCE_ADAPTER_NAMED_SITE_PROFILE_STORE_RUNTIME.md").read_text(encoding="utf-8")
assert "Source Adapter Named-Site Profile Store Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_NAMED_SITE_PROFILE_STORE_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_NAMED_SITE_PROFILE_STORE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_STAGE" in doc
print("Source Adapter Named-Site Profile Store Runtime docs self-test passed.")
