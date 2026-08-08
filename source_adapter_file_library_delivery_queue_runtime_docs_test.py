from pathlib import Path

doc = Path("SOURCE_ADAPTER_FILE_LIBRARY_DELIVERY_QUEUE_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter File Library Delivery Queue Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_FILE_LIBRARY_DELIVERY_QUEUE_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_FILE_LIBRARY_DELIVERY_QUEUE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter File Library Delivery Queue Runtime docs self-test passed.")
