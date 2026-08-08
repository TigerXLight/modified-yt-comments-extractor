from __future__ import annotations

import json

from source_fixture_capture_results import (
    build_fixture_capture_result_bundle,
    source_fixture_capture_result_bundle_to_json,
    validate_fixture_capture_result_bundle,
)


def test_fixture_capture_bundle_contains_article_outline_comments_and_livechat() -> None:
    bundle = build_fixture_capture_result_bundle()
    data = bundle.to_dict()
    assert data["article_result"]["text"]
    assert data["page_outline_result"]["outline_lines"]
    assert data["comment_count"] >= 2
    assert data["livechat_event_count"] >= 1
    assert data["no_live_execution"] is True
    assert data["browser_automation_performed"] is False


def test_screenshot_contracts_distinguish_faithful_derived_and_blocked() -> None:
    data = build_fixture_capture_result_bundle().to_dict()
    by_fidelity = {row["fidelity"]: row for row in data["screenshot_results"]}
    assert by_fidelity["faithful_viewport"]["labelled_faithful"] is True
    assert by_fidelity["derived_expanded_stitched"]["derived_modifications"]
    assert by_fidelity["derived_expanded_stitched"]["labelled_faithful"] is False
    assert by_fidelity["protected_black_frame_blocked"]["protected_output_blocked"] is True
    assert validate_fixture_capture_result_bundle(data) == ()


def test_challenge_and_encoded_payload_boundaries_are_safe() -> None:
    data = build_fixture_capture_result_bundle().to_dict()
    assert all(not row["token_stored"] for row in data["challenge_states"])
    assert any(row["encrypted_or_inaccessible"] for row in data["encoded_payload_results"])
    unsafe = json.loads(source_fixture_capture_result_bundle_to_json(build_fixture_capture_result_bundle()))
    unsafe["challenge_states"][0]["token_stored"] = True
    unsafe["encoded_payload_results"][0]["keys_invented_or_bypassed"] = True
    errors = validate_fixture_capture_result_bundle(unsafe)
    assert "challenge_token_stored" in errors
    assert "encoded_payload_bypass_not_allowed" in errors


def test_serialization_is_deterministic() -> None:
    assert source_fixture_capture_result_bundle_to_json(build_fixture_capture_result_bundle()) == (
        source_fixture_capture_result_bundle_to_json(build_fixture_capture_result_bundle())
    )


if __name__ == "__main__":
    test_fixture_capture_bundle_contains_article_outline_comments_and_livechat()
    test_screenshot_contracts_distinguish_faithful_derived_and_blocked()
    test_challenge_and_encoded_payload_boundaries_are_safe()
    test_serialization_is_deterministic()
    print("source_fixture_capture_results_test.py passed")
