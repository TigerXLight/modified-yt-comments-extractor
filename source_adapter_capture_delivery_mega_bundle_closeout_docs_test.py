from pathlib import Path

doc = Path("SOURCE_ADAPTER_CAPTURE_DELIVERY_MEGA_BUNDLE_CLOSEOUT.md").read_text(encoding="utf-8")
assert "# Source Adapter Capture Delivery Mega Bundle Closeout" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_CAPTURE_DELIVERY_MEGA_BUNDLE_CLOSEOUT_BUILT" in doc
assert "SOURCE_ADAPTER_CAPTURE_DELIVERY_MEGA_BUNDLE_CLOSEOUT_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Capture Delivery Mega Bundle Closeout docs self-test passed.")
