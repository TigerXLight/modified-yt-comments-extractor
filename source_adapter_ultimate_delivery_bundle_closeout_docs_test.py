from pathlib import Path

doc = Path("SOURCE_ADAPTER_ULTIMATE_DELIVERY_BUNDLE_CLOSEOUT.md").read_text(encoding="utf-8")
assert "# Source Adapter Ultimate Delivery Bundle Closeout" in doc
assert "KEYS/ACCOUNTS" in doc
assert "Online ASR" in doc
assert "large-v3 Vulkan" in doc
assert "SOURCE_ADAPTER_ULTIMATE_DELIVERY_BUNDLE_CLOSEOUT_BUILT" in doc
assert "SOURCE_ADAPTER_ULTIMATE_DELIVERY_BUNDLE_CLOSEOUT_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Ultimate Delivery Bundle Closeout docs self-test passed.")
