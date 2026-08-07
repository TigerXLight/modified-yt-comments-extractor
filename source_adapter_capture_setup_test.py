from __future__ import annotations

from source_adapter_capture_setup import (
    SourceAdapterCaptureSetupError,
    build_source_adapter_capture_setup,
    demo_source_selection_package,
)


def test_build_source_adapter_capture_setup_ready() -> None:
    package = build_source_adapter_capture_setup(demo_source_selection_package())
    assert package["schema_version"] == "source_adapter_capture_setup_package_v1"
    assert package["capture_setup_status"] == "SOURCE_ADAPTER_CAPTURE_SETUP_READY"
    assert package["adapter_count"] == 1
    assert package["setup_count"] == 1
    assert package["capture_setup_plan"]["setup_rows"][0]["adapter_id"] == "article"
    assert package["artifact_intake_plan"]["artifact_intake_status"] == "READY_FOR_EXPLICIT_ARTIFACT_INTAKE"
    assert package["lightweight_browser_capture_setup_handoff"]["handoff_status"] == "READY_FOR_APPROVED_BROWSER_CAPTURE_SETUP"
    assert package["operator_summary"]["manual_or_live_actions_started"] is False


def test_blocks_when_selection_not_ready() -> None:
    selection = demo_source_selection_package()
    selection["selection_status"] = "DRAFT"
    package = build_source_adapter_capture_setup(selection)
    assert package["capture_setup_status"] == "SOURCE_ADAPTER_CAPTURE_SETUP_BLOCKED"
    assert package["issue_count"] == 1


def test_rejects_duplicate_source_selection_options() -> None:
    selection = demo_source_selection_package()
    options = selection["source_selection_catalog"]["options"]
    options.append(dict(options[0]))
    try:
        build_source_adapter_capture_setup(selection)
    except SourceAdapterCaptureSetupError as exc:
        assert "duplicate adapter_id" in str(exc)
    else:
        raise AssertionError("duplicate adapter_id should fail")


def test_rejects_local_path_fields() -> None:
    selection = demo_source_selection_package()
    selection["source_selection_catalog"]["options"][0]["local_path"] = "C:/secret"
    try:
        build_source_adapter_capture_setup(selection)
    except SourceAdapterCaptureSetupError as exc:
        assert "local path fields" in str(exc)
    else:
        raise AssertionError("local path fields should fail")


if __name__ == "__main__":
    test_build_source_adapter_capture_setup_ready()
    test_blocks_when_selection_not_ready()
    test_rejects_duplicate_source_selection_options()
    test_rejects_local_path_fields()
    print("Source Adapter Capture Setup self-test passed.")
