from pathlib import Path

doc = Path("SOURCE_ADAPTER_MSN_LIVE_PROFILE_EXECUTOR_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter MSN Live Profile Executor Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "Online ASR" in doc
assert "large-v3 Vulkan" in doc
assert "SOURCE_ADAPTER_MSN_LIVE_PROFILE_EXECUTOR_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_MSN_LIVE_PROFILE_EXECUTOR_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter MSN Live Profile Executor Runtime docs self-test passed.")
