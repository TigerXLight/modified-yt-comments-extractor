from __future__ import annotations

from source_operator_workflow_sidecars import (
    build_operator_workflow_sidecar_bundle,
    operator_workflow_sidecar_bundle_to_json,
)


def test_operator_workflow_sidecar_bundle_exposes_all_execution_workflows() -> None:
    bundle = build_operator_workflow_sidecar_bundle()
    data = bundle.to_dict()
    assert data["sidecar_count"] == 5
    assert data["operator_approval_gateway"]["payload"]["preview_gateway"]["blocked_count"] > 0
    assert data["operator_approval_gateway"]["payload"]["approved_local_temp_gateway"]["approved_count"] > 0
    assert data["unified_execution_jobs"]["payload"]["runner_available"] is True
    assert data["local_e2e_total_export"]["payload"]["local_e2e_total_export_callable"] is True
    assert data["live_smoke_runner"]["payload"]["plan_count"] == 11
    assert data["database_movement_operator_workflow"]["payload"]["approved_copy_move_callable"] is True
    assert data["database_movement_operator_workflow"]["payload"]["automatic_classification"] is False
    assert data["live_execution_performed"] is False
    assert data["real_user_evidence_moved"] is False
    assert "api_key" not in operator_workflow_sidecar_bundle_to_json(bundle)


if __name__ == "__main__":
    test_operator_workflow_sidecar_bundle_exposes_all_execution_workflows()
    print("source_operator_workflow_sidecars_test.py passed")
