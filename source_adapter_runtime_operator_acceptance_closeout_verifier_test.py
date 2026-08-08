from __future__ import annotations

from copy import deepcopy

from source_adapter_runtime_operator_acceptance_closeout import build_source_adapter_runtime_operator_acceptance_closeout
from source_adapter_runtime_operator_acceptance_closeout_test import fixture_runtime_ui_provider_integration_bridge
from source_adapter_runtime_operator_acceptance_closeout_verifier import verify_source_adapter_runtime_operator_acceptance_closeout


def test_verifier_accepts_valid_package() -> None:
    package = build_source_adapter_runtime_operator_acceptance_closeout(fixture_runtime_ui_provider_integration_bridge())
    assert verify_source_adapter_runtime_operator_acceptance_closeout(package)["verified"] is True


def test_verifier_rejects_missing_gui_routes() -> None:
    package = build_source_adapter_runtime_operator_acceptance_closeout(fixture_runtime_ui_provider_integration_bridge())
    broken = deepcopy(package)
    broken["source_adapter_gui_controller_binding_manifest"]["routes"] = []
    broken["source_adapter_gui_controller_binding_manifest"]["route_count"] = 0
    result = verify_source_adapter_runtime_operator_acceptance_closeout(broken)
    assert result["verified"] is False
    assert any("GUI route capability" in issue for issue in result["issues"])


if __name__ == "__main__":
    test_verifier_accepts_valid_package()
    test_verifier_rejects_missing_gui_routes()
    print("Source Adapter Runtime Operator Acceptance Closeout verifier self-test passed.")
