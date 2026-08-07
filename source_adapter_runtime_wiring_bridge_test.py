from __future__ import annotations

from copy import deepcopy

from source_adapter_pipeline_closeout_bridge import build_source_adapter_pipeline_closeout_bridge
from source_adapter_pipeline_closeout_bridge_test import fixture_archive_review_bridge
from source_adapter_runtime_wiring_bridge import (
    build_source_adapter_runtime_wiring_bridge,
    runtime_capability_catalog,
)
from source_adapter_runtime_wiring_bridge_verifier import verify_source_adapter_runtime_wiring_bridge


def fixture_pipeline_closeout_bridge() -> dict:
    return build_source_adapter_pipeline_closeout_bridge(fixture_archive_review_bridge(), operator_notes=["fixture closeout"])


def test_runtime_capability_catalog_covers_operator_surfaces() -> None:
    capability_ids = {item["capability_id"] for item in runtime_capability_catalog()}
    assert {
        "operator_url_fetch",
        "browser_launch",
        "folder_scan",
        "credential_lookup",
        "archive_submit",
        "release_upload",
        "app_registry_mutation",
        "file_library_publication",
    }.issubset(capability_ids)


def test_build_runtime_wiring_bridge_dry_run_receipts() -> None:
    package = build_source_adapter_runtime_wiring_bridge(
        fixture_pipeline_closeout_bridge(),
        operator_approval_id="approval.runtime.fixture",
        runtime_inputs={
            "fixture_adapter": {
                "artifact_folder": "T:/fixture/artifacts",
                "credential_ref": "keys://archive_today/default",
                "archive_provider_task": {"provider_id": "archive_today"},
                "release_artifact": "release/source.zip",
                "library_destination": "/SourceEvidence/fixture.json",
            }
        },
        operator_notes=["wire runtime surfaces"],
    )
    assert package["runtime_wiring_status"] == "SOURCE_ADAPTER_RUNTIME_ACTIONS_WIRED"
    assert package["runtime_action_count"] == 8
    assert package["runtime_receipt_count"] == 8
    assert package["source_adapter_runtime_execution_handoff"]["handoff_status"] == "SOURCE_ADAPTER_RUNTIME_RECEIPTS_BUILT"
    assert verify_source_adapter_runtime_wiring_bridge(package)["verified"] is True


def test_plan_only_marks_ready_for_operator_execution() -> None:
    package = build_source_adapter_runtime_wiring_bridge(
        fixture_pipeline_closeout_bridge(),
        enabled_capabilities=["operator_url_fetch", "browser_launch"],
        execution_mode="plan_only",
    )
    assert package["runtime_action_count"] == 2
    assert package["runtime_receipt_count"] == 0
    assert package["source_adapter_runtime_execution_handoff"]["handoff_status"] == "READY_FOR_OPERATOR_APPROVED_RUNTIME_EXECUTION"
    assert verify_source_adapter_runtime_wiring_bridge(package)["verified"] is True


def test_operator_approved_executor_builds_receipts() -> None:
    calls: list[str] = []

    def executor(action: dict) -> dict:
        calls.append(action["runtime_action_id"])
        return {
            "execution_status": "EXECUTED_BY_TEST_EXECUTOR",
            "receipt_role": action["receipt_role"],
            "executor": "fixture_executor",
            "external_effect_recorded": True,
            "reference": f"receipt://{action['runtime_action_id']}",
        }

    package = build_source_adapter_runtime_wiring_bridge(
        fixture_pipeline_closeout_bridge(),
        enabled_capabilities=["archive_submit", "release_upload"],
        execution_mode="operator_approved_executor",
        operator_approval_id="approval.executor.fixture",
        executor=executor,
    )
    assert calls and len(calls) == 2
    assert package["runtime_receipt_count"] == 2
    assert package["source_adapter_runtime_action_receipt_batch"]["runtime_action_receipts"][0]["external_effect_recorded"] is True
    assert verify_source_adapter_runtime_wiring_bridge(package)["verified"] is True


def test_rejects_unfinished_pipeline_closeout_handoff() -> None:
    fixture = deepcopy(fixture_pipeline_closeout_bridge())
    fixture["source_adapter_shared_pipeline_roadmap_closeout_handoff"]["handoff_status"] = "SOURCE_ADAPTER_SHARED_PIPELINE_FOLLOW_UP_REQUIRED"
    try:
        build_source_adapter_runtime_wiring_bridge(fixture)
    except ValueError as exc:
        assert "SOURCE_ADAPTER_SHARED_PIPELINE_COMPLETE" in str(exc)
    else:
        raise AssertionError("expected unfinished pipeline closeout rejection")


if __name__ == "__main__":
    test_runtime_capability_catalog_covers_operator_surfaces()
    test_build_runtime_wiring_bridge_dry_run_receipts()
    test_plan_only_marks_ready_for_operator_execution()
    test_operator_approved_executor_builds_receipts()
    test_rejects_unfinished_pipeline_closeout_handoff()
    print("Source Adapter Runtime Wiring Bridge self-test passed.")
