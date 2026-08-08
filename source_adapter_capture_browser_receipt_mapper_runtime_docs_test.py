from pathlib import Path

doc = Path("SOURCE_ADAPTER_CAPTURE_BROWSER_RECEIPT_MAPPER_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Capture Browser Receipt Mapper Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "Online ASR" in doc
assert "large-v3 Vulkan" in doc
assert "SOURCE_ADAPTER_CAPTURE_BROWSER_RECEIPT_MAPPER_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_CAPTURE_BROWSER_RECEIPT_MAPPER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Capture Browser Receipt Mapper Runtime docs self-test passed.")
