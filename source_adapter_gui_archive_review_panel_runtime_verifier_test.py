from source_adapter_gui_archive_review_panel_runtime import example_source_adapter_gui_archive_review_panel_runtime_package
from source_adapter_gui_archive_review_panel_runtime_verifier import verify_source_adapter_gui_archive_review_panel_runtime

package = example_source_adapter_gui_archive_review_panel_runtime_package()
verified = verify_source_adapter_gui_archive_review_panel_runtime(package)
assert verified["verified"], verified
broken = dict(package)
broken["status"] = "BROKEN"
assert not verify_source_adapter_gui_archive_review_panel_runtime(broken)["verified"]
print("Source Adapter GUI Archive Review Panel Runtime verifier self-test passed.")
