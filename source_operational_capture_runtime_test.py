from __future__ import annotations

import json

from source_operational_capture_runtime import (
    OperationalResultStatus,
    build_default_operational_fixture_matrix,
    build_fixture_operational_capture_runtime_bundle,
    source_operational_capture_runtime_bundle_to_json,
    validate_operational_runtime_result,
)


def test_fixture_matrix_covers_required_categories() -> None:
    fixtures = build_default_operational_fixture_matrix()
    categories = {fixture.category for fixture in fixtures}
    assert {
        "article",
        "comments",
        "decoded_state",
        "challenge",
        "livechat",
        "media",
        "rendered_citation",
        "archive",
        "archivebox",
    }.issubset(categories)
    assert any(fixture.fixture_id == "fixture_comments_virtualized" for fixture in fixtures)
    assert all(not fixture.external_network_required for fixture in fixtures)
    assert all(not fixture.live_browser_required for fixture in fixtures)


def test_runtime_bundle_serializes_deterministically() -> None:
    first = build_fixture_operational_capture_runtime_bundle()
    second = build_fixture_operational_capture_runtime_bundle()
    assert source_operational_capture_runtime_bundle_to_json(first) == (
        source_operational_capture_runtime_bundle_to_json(second)
    )
    data = json.loads(source_operational_capture_runtime_bundle_to_json(first))
    assert data["fixture_count"] >= 25
    assert data["runtime_result_count"] == 1
    assert data["completed_evidence_claimed"] is False
    assert data["no_live_execution"] is True


def test_runtime_result_rejects_unsafe_completion_claims() -> None:
    bundle = build_fixture_operational_capture_runtime_bundle()
    result = bundle.runtime_results[0].to_dict()
    assert validate_operational_runtime_result(result) == ()
    unsafe = dict(result)
    unsafe["result_status"] = OperationalResultStatus.FIXTURE_TESTED.value
    unsafe["completed_evidence_claimed"] = True
    unsafe["live_network_performed"] = True
    errors = validate_operational_runtime_result(unsafe)
    assert "unsafe_flag_true:completed_evidence_claimed" in errors
    assert "unsafe_flag_true:live_network_performed" in errors


if __name__ == "__main__":
    test_fixture_matrix_covers_required_categories()
    test_runtime_bundle_serializes_deterministically()
    test_runtime_result_rejects_unsafe_completion_claims()
    print("source_operational_capture_runtime_test.py passed")
