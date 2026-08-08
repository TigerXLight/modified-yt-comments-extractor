from __future__ import annotations

from copy import deepcopy

from source_adapter_runtime_controller_provider_closeout import build_source_adapter_runtime_controller_provider_closeout
from source_adapter_runtime_controller_provider_closeout_test import fixture_runtime_operator_acceptance_closeout
from source_adapter_runtime_controller_provider_closeout_verifier import verify_source_adapter_runtime_controller_provider_closeout


def test_verifier_accepts_package() -> None:
    package = build_source_adapter_runtime_controller_provider_closeout(fixture_runtime_operator_acceptance_closeout())
    result = verify_source_adapter_runtime_controller_provider_closeout(package)
    assert result["verified"] is True
    assert result["dispatch_row_count"] == 8


def test_verifier_rejects_missing_controller_row() -> None:
    package = build_source_adapter_runtime_controller_provider_closeout(fixture_runtime_operator_acceptance_closeout())
    broken = deepcopy(package)
    broken["source_adapter_runtime_controller_install_manifest"]["controller_install_rows"].pop()
    result = verify_source_adapter_runtime_controller_provider_closeout(broken)
    assert result["verified"] is False
    assert result["issue_count"] > 0


if __name__ == "__main__":
    test_verifier_accepts_package()
    test_verifier_rejects_missing_controller_row()
    print("Source Adapter Runtime Controller Provider Closeout verifier self-test passed.")
