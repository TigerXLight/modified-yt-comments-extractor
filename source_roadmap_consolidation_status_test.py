from source_roadmap_consolidation_status import (
    RoadmapCoverageStatus,
    build_default_roadmap_consolidation_status,
    roadmap_consolidation_markdown_table,
)


def test_status_records_evidence_file_movement_not_done() -> None:
    status = build_default_roadmap_consolidation_status()
    data = status.to_dict()
    assert data["evidence_file_movement_done"] is False
    assert data["completed_evidence_claim_allowed"] is False
    movement = next(item for item in status.items if item.requirement == "Evidence file movement/completed evidence")
    assert movement.status == RoadmapCoverageStatus.OPERATOR_APPROVAL_REQUIRED
    assert "must not be claimed" in movement.remaining_gap


def test_status_has_expected_metadata_contracts() -> None:
    status = build_default_roadmap_consolidation_status()
    implemented = {item.requirement for item in status.by_status(RoadmapCoverageStatus.IMPLEMENTED_METADATA)}
    assert "Source websites/method catalogue" in implemented
    assert "Source URL media UI roadmap" in implemented
    assert "Database recognition/reclassification" in implemented
    assert "Behavior/action log and accountable witnesses" in implemented


def test_markdown_table_is_renderable() -> None:
    table = roadmap_consolidation_markdown_table()
    assert "| Requirement | Status |" in table
    assert "Evidence file movement/completed evidence" in table
    assert "operator_approval_required" in table


def main() -> None:
    test_status_records_evidence_file_movement_not_done()
    test_status_has_expected_metadata_contracts()
    test_markdown_table_is_renderable()
    print("source_roadmap_consolidation_status_test: OK")


if __name__ == "__main__":
    main()
