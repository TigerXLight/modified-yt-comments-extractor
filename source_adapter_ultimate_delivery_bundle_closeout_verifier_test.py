from source_adapter_ultimate_delivery_bundle_closeout import example_source_adapter_ultimate_delivery_bundle_closeout_package
from source_adapter_ultimate_delivery_bundle_closeout_verifier import verify_source_adapter_ultimate_delivery_bundle_closeout

package = example_source_adapter_ultimate_delivery_bundle_closeout_package()
verified = verify_source_adapter_ultimate_delivery_bundle_closeout(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_ultimate_delivery_bundle_closeout(broken)["verified"]
print("Source Adapter Ultimate Delivery Bundle Closeout verifier self-test passed.")
