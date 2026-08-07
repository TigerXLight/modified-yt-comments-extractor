from __future__ import annotations

from source_adapter_coverage import PIPELINE_STAGE_IDS, build_source_adapter_coverage
from source_adapter_coverage_verifier import verify_source_adapter_coverage


def _sample_adapters():
    return [
        {
            "adapter_id": "msn_manual",
            "display_name": "MSN manual capture",
            "domains": ["msn.com"],
            "capture_surfaces": ["article", "comments_shadow_root"],
            "implemented_stages": list(PIPELINE_STAGE_IDS),
            "requires_lightweight_browser": True,
        },
        {
            "adapter_id": "article_generic",
            "display_name": "Generic article site",
            "domains": ["example.com"],
            "capture_surfaces": ["article", "comments"],
            "implemented_stages": ["source_discovery"],
            "requires_lightweight_browser": True,
        },
    ]


def test_framework_covers_many_adapters_without_cloning_msn():
    report = build_source_adapter_coverage(_sample_adapters())
    payload = report.to_dict()
    assert payload["coverage_strategy"] == "one_framework_many_adapters"
    assert payload["adapter_count"] == 2
    assert len(payload["stage_matrix"]) == len(PIPELINE_STAGE_IDS)
    assert all(row["coverage_mode"] == "shared_framework" for row in payload["stage_matrix"])
    assert all(row["adapter_specific_module_required"] is False for row in payload["stage_matrix"])
    generic = next(item for item in payload["adapter_work_items"] if item["adapter_id"] == "article_generic")
    assert generic["missing_stage_count"] == len(PIPELINE_STAGE_IDS) - 1
    assert generic["work_mode"] == "adapter_spec_mapping"


def test_lightweight_browser_is_planned_but_not_started():
    report = build_source_adapter_coverage(_sample_adapters())
    browser = report.to_dict()["lightweight_browser_plan"]
    assert browser["execution_mode"] == "operator_approved_manual_only"
    assert browser["live_network_default"] is False
    assert browser["approval_required_before_navigation"] is True
    assert any(item["capability_id"] == "dom_snapshot" for item in browser["capabilities"])
    assert report.to_dict()["operator_summary"]["manual_or_live_actions_started"] is False


def test_verifier_accepts_shared_framework_report():
    report = build_source_adapter_coverage(_sample_adapters())
    verification = verify_source_adapter_coverage(report.to_dict())
    assert verification["verified"] is True
    assert verification["issue_count"] == 0


if __name__ == "__main__":
    test_framework_covers_many_adapters_without_cloning_msn()
    test_lightweight_browser_is_planned_but_not_started()
    test_verifier_accepts_shared_framework_report()
    print("Source Adapter coverage framework self-test passed.")
