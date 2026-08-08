from __future__ import annotations

from copy import deepcopy

from source_adapter_runtime_gui_provider_implementation import example_runtime_gui_provider_implementation_package
from source_adapter_runtime_gui_provider_implementation_verifier import verify_source_adapter_runtime_gui_provider_implementation


def main() -> None:
    package = example_runtime_gui_provider_implementation_package()
    result = verify_source_adapter_runtime_gui_provider_implementation(package)
    assert result["verified"] is True
    assert result["issue_count"] == 0
    broken = deepcopy(package)
    broken["source_adapter_runtime_gui_provider_implementation_handoff"]["handoff_status"] = "BROKEN"
    broken_result = verify_source_adapter_runtime_gui_provider_implementation(broken)
    assert broken_result["verified"] is False
    print("Source Adapter Runtime GUI Provider Implementation verifier self-test passed.")


if __name__ == "__main__":
    main()
