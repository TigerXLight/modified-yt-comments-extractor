from pathlib import Path

doc = Path("SOURCE_ADAPTER_COMMENTS_PROFILE_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Comments Profile Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_COMMENTS_PROFILE_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_COMMENTS_PROFILE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Comments Profile Runtime docs self-test passed.")
