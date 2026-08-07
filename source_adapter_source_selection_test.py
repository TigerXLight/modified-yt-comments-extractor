from __future__ import annotations

from source_adapter_source_selection import (
    SourceAdapterSourceSelectionError,
    build_source_adapter_source_selection,
    demo_rollout_package,
)


def test_build_source_adapter_source_selection_ready() -> None:
    package = build_source_adapter_source_selection(demo_rollout_package())
    assert package["schema_version"] == "source_adapter_source_selection_package_v1"
    assert package["selection_status"] == "SOURCE_ADAPTER_SELECTION_READY"
    assert package["adapter_count"] == 1
    assert package["route_count"] == 1
    assert package["source_selection_catalog"]["options"][0]["adapter_id"] == "article"
    assert package["capture_route_index"]["routes"][0]["requires_manual_approval_before_live_navigation"] is True
    assert package["source_selection_capture_handoff"]["handoff_status"] == "READY_FOR_CAPTURE_SETUP_WIRING"
    assert package["operator_summary"]["manual_or_live_actions_started"] is False


def test_blocks_when_rollout_not_ready() -> None:
    rollout = demo_rollout_package()
    rollout["registry_rollout_status"] = "DRAFT"
    package = build_source_adapter_source_selection(rollout)
    assert package["selection_status"] == "SOURCE_ADAPTER_SELECTION_BLOCKED"
    assert package["issue_count"] == 1


def test_rejects_duplicate_adapters() -> None:
    rollout = demo_rollout_package()
    options = rollout["source_adapter_selection_option_index"]["options"]
    options.append(dict(options[0]))
    try:
        build_source_adapter_source_selection(rollout)
    except SourceAdapterSourceSelectionError as exc:
        assert "duplicate adapter_id" in str(exc)
    else:
        raise AssertionError("duplicate adapter_id should fail")


def test_rejects_local_path_fields() -> None:
    rollout = demo_rollout_package()
    rollout["source_adapter_selection_option_index"]["options"][0]["local_path"] = "C:/secret"
    try:
        build_source_adapter_source_selection(rollout)
    except SourceAdapterSourceSelectionError as exc:
        assert "local path fields" in str(exc)
    else:
        raise AssertionError("local path fields should fail")


if __name__ == "__main__":
    test_build_source_adapter_source_selection_ready()
    test_blocks_when_rollout_not_ready()
    test_rejects_duplicate_adapters()
    test_rejects_local_path_fields()
    print("Source Adapter Source Selection self-test passed.")
