from pathlib import Path

doc = Path("SOURCE_ADAPTER_FINAL_DELIVERY_CLOSURE_BUNDLE_CLOSEOUT.md").read_text(encoding="utf-8")
assert "# Source Adapter Final Delivery Closure Bundle Closeout" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_FINAL_DELIVERY_CLOSURE_BUNDLE_CLOSEOUT_BUILT" in doc
assert "SOURCE_ADAPTER_FINAL_DELIVERY_CLOSURE_BUNDLE_CLOSEOUT_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Final Delivery Closure Bundle Closeout docs self-test passed.")
