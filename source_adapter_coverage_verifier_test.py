from __future__ import annotations

from source_adapter_coverage import build_source_adapter_coverage
from source_adapter_coverage_verifier import verify_source_adapter_coverage


def test_verifier_rejects_live_default_browser():
    report = build_source_adapter_coverage([{"adapter_id": "x", "display_name": "X", "domains": ["x.example"]}]).to_dict()
    report["lightweight_browser_plan"]["live_network_default"] = True
    result = verify_source_adapter_coverage(report)
    assert result["verified"] is False
    assert any("live_network_default" in issue for issue in result["issues"])


def test_verifier_rejects_adapter_specific_stage_requirement():
    report = build_source_adapter_coverage([{"adapter_id": "x", "display_name": "X", "domains": ["x.example"]}]).to_dict()
    report["stage_matrix"][0]["adapter_specific_module_required"] = True
    result = verify_source_adapter_coverage(report)
    assert result["verified"] is False
    assert any("adapter_specific_module_required" in issue for issue in result["issues"])


if __name__ == "__main__":
    test_verifier_rejects_live_default_browser()
    test_verifier_rejects_adapter_specific_stage_requirement()
    print("Source Adapter coverage framework verifier self-test passed.")
