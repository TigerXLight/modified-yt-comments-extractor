from source_named_site_priority_plan import (
    build_source_named_site_priority_plan,
    source_named_site_priority_plan_to_json,
    validate_source_named_site_priority_plan,
)


def test_named_site_priority_plan_lists_future_operator_approval_targets() -> None:
    plan = build_source_named_site_priority_plan()
    data = plan.to_dict()
    rendered = source_named_site_priority_plan_to_json(plan)

    assert plan.row_count == 9
    assert plan.approval_required_count == 9
    assert plan.selector_audit_required_count == 1
    assert [row.priority_rank for row in plan.rows] == list(range(1, 10))
    assert plan.rows[0].method_id == "msn_article"
    assert any(row.method_id == "generic_comments_site_specific_selector" for row in plan.rows)
    generic_comments = next(
        row for row in plan.rows if row.method_id == "generic_comments_site_specific_selector"
    )
    assert generic_comments.next_action == "perform_named_site_selector_audit_with_explicit_approval"
    assert "site_specific_selector_review_note" in generic_comments.planned_operator_inputs
    assert "APPROVAL_REQUIRED" in rendered
    assert "live verified" not in rendered.lower()
    assert "completed evidence" not in rendered.lower()
    assert data["metadata_only"] is True
    assert data["live_execution_performed"] is False
    validate_source_named_site_priority_plan(data)


def test_named_site_priority_plan_validation_rejects_execution_claims() -> None:
    data = build_source_named_site_priority_plan().to_dict()
    data["rows"][0]["download_performed"] = True

    try:
        validate_source_named_site_priority_plan(data)
    except ValueError as error:
        assert "download_performed" in str(error)
    else:
        raise AssertionError("Unsafe named-site priority row should be rejected")


def run_self_test() -> None:
    test_named_site_priority_plan_lists_future_operator_approval_targets()
    test_named_site_priority_plan_validation_rejects_execution_claims()


if __name__ == "__main__":
    run_self_test()
    print("Source named-site priority plan self-test passed.")
