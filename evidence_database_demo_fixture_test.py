from evidence_database_demo_fixture import (
    EVIDENCE_DATABASE_DEMO_FIXTURE_VERSION,
    EVIDENCE_DATABASE_DEMO_ROOT_ID,
    EVIDENCE_DATABASE_DEMO_SCOPE,
    EVIDENCE_DATABASE_DEMO_TAXONOMY_ID,
    build_synthetic_evidence_database_demo_fixture,
)
from evidence_database_index import EvidenceClassificationValue, stable_json_dumps


def run_self_test() -> None:
    fixture = build_synthetic_evidence_database_demo_fixture()
    assert fixture.fixture_version == EVIDENCE_DATABASE_DEMO_FIXTURE_VERSION
    assert fixture.scope == EVIDENCE_DATABASE_DEMO_SCOPE
    assert fixture.root.root_id == EVIDENCE_DATABASE_DEMO_ROOT_ID
    assert fixture.root.root_path == "synthetic_fixture/evidence_demo/root"
    assert fixture.root.broad_scan_allowed is False
    assert fixture.root.dry_run_required is True
    assert fixture.root.moves_require_explicit_approval is True
    assert fixture.taxonomy_version.taxonomy_version_id == EVIDENCE_DATABASE_DEMO_TAXONOMY_ID
    assert fixture.taxonomy_version.dimension_order == ("fixture_category", "review_state")

    assert fixture.classification_values() == (
        "unknown",
        "not_evidenced",
        "proposed",
        "user_confirmed",
        "rejected",
        "superseded",
    )
    assert tuple(row.classification_value for row in fixture.preview_result.rows) == (
        EvidenceClassificationValue.NOT_EVIDENCED,
        EvidenceClassificationValue.PROPOSED,
        EvidenceClassificationValue.REJECTED,
        EvidenceClassificationValue.SUPERSEDED,
        EvidenceClassificationValue.UNKNOWN,
        EvidenceClassificationValue.USER_CONFIRMED,
    )
    assert fixture.preview_result.record_count == 6
    assert fixture.preview_result.supplied_records_only is True
    assert fixture.preview_result.broad_scan_performed is False
    assert fixture.preview_result.file_operation_performed is False
    assert fixture.preview_result.to_dict()["group_counts"] == {
        "not_evidenced": 1,
        "proposed": 1,
        "rejected": 1,
        "superseded": 1,
        "unknown": 1,
        "user_confirmed": 1,
    }

    for record in fixture.records:
        assert record.database_root_id == fixture.root.root_id
        assert record.taxonomy_version_id == fixture.taxonomy_version.taxonomy_version_id
        assert record.identity.source_url.startswith("https://example.test/evidence-demo/")
        assert record.identity.local_path_hint.startswith("synthetic_fixture/evidence_demo/")
        assert record.classification_state.sensitive_dimensions_present == ()
        assert record.classification_state.weak_inference_prohibited is True
        assert record.path_records[0].file_operation_performed is False
        assert record.placement_proposals[0].file_operation_performed is False
        assert record.reclassification_proposals[0].file_operation_performed is False
        assert record.evidence_basis[0].sensitive_basis_confirmed is False

    plan = fixture.apply_plan
    assert len(fixture.decisions) == 3
    assert len(plan.entries) == 3
    assert plan.dry_run is True
    assert plan.execute_file_moves is False
    assert plan.execute_classification_changes is False
    assert plan.file_operation_performed is False
    assert plan.destructive_action_not_implemented is True
    assert plan.warnings == ("synthetic_fixture_apply_plan_not_executed",)
    assert all(entry.file_operation_performed is False for entry in plan.entries)
    assert all(entry.classification_change_executed is False for entry in plan.entries)

    serialized = stable_json_dumps(
        {
            "records": [record.to_dict() for record in fixture.records],
            "root": fixture.root.to_dict(),
            "taxonomy": fixture.taxonomy_version.to_dict(),
        }
    )
    assert "synthetic_fixture/evidence_demo" in serialized
    assert "example.test/evidence-demo" in serialized
    assert "C:/Users" not in serialized
    assert "T:/References" not in serialized
    assert "api_key" not in serialized.lower()
    assert "authorization" not in serialized.lower()
    assert "cookie" not in serialized.lower()
    assert "religion" not in serialized.lower()
    assert "ethnicity" not in serialized.lower()
    assert "nationality" not in serialized.lower()
    assert "politics" not in serialized.lower()


if __name__ == "__main__":
    run_self_test()
    print("Evidence database demo fixture self-test passed.")
