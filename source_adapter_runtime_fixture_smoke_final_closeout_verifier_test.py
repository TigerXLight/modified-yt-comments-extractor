from __future__ import annotations

from copy import deepcopy

from source_adapter_runtime_controller_provider_closeout import build_source_adapter_runtime_controller_provider_closeout
from source_adapter_runtime_controller_provider_closeout_test import fixture_runtime_operator_acceptance_closeout
from source_adapter_runtime_fixture_smoke_final_closeout import build_source_adapter_runtime_fixture_smoke_final_closeout
from source_adapter_runtime_fixture_smoke_final_closeout_verifier import verify_source_adapter_runtime_fixture_smoke_final_closeout


def test_verifier_accepts_valid_package() -> None:
    controller = build_source_adapter_runtime_controller_provider_closeout(fixture_runtime_operator_acceptance_closeout())
    package = build_source_adapter_runtime_fixture_smoke_final_closeout(controller)
    result = verify_source_adapter_runtime_fixture_smoke_final_closeout(package)
    assert result["verified"] is True
    assert result["capability_count"] == 8


def test_verifier_rejects_missing_smoke_ready_status() -> None:
    controller = build_source_adapter_runtime_controller_provider_closeout(fixture_runtime_operator_acceptance_closeout())
    package = build_source_adapter_runtime_fixture_smoke_final_closeout(controller)
    broken = deepcopy(package)
    broken["source_adapter_manual_live_smoke_runbook"]["manual_live_smoke_runbook_rows"][0]["runbook_status"] = "different"
    result = verify_source_adapter_runtime_fixture_smoke_final_closeout(broken)
    assert result["verified"] is False
    assert any("runbook status" in issue for issue in result["issues"])


if __name__ == "__main__":
    test_verifier_accepts_valid_package()
    test_verifier_rejects_missing_smoke_ready_status()
    print("Source Adapter Runtime Fixture Smoke Final Closeout verifier self-test passed.")
