import json

from source_reference_intake import (
    ReferencePackIntakeRecord,
    ReferencePackKind,
    ReferenceUseBoundary,
    build_reference_pack_intake_summary,
    build_reference_pack_intake_summary_text,
    reference_pack_intake_record_to_json,
    reference_pack_intake_records,
    reference_pack_intake_summary_to_json,
    validate_reference_pack_intake_records,
)


EXPECTED_HASHES = {
    "rev4_site_capture_preparation_pack": "bd326f07958380ceb572cdaeabb32d3cb9f9d29286642491605f6e3b5635787b",
    "extension_reference_1_unknown_background_bundle": "b6ae72c127dd8ba5d976e48879c973829d936d7e813e8f3d9e5d771683bfe337",
    "extension_reference_2_mv3_offscreen_managed_schema": "ae051be084b285a0881fb77f88cf851285ae320cb1af0e187bb81078790596ab",
    "extension_reference_3_pdf_capture_style_surface": "dfb5aa35ad28178e913c08a060dd6d3176a168b8d09c282fa09318e9a0f6501d",
}


def test_reference_pack_records_are_deterministic_and_reference_only() -> None:
    records = reference_pack_intake_records()
    repeated = reference_pack_intake_records()

    assert records == repeated
    assert len(records) == 4
    assert [record.pack_id for record in records] == sorted(EXPECTED_HASHES)
    assert {record.pack_id: record.sha256 for record in records} == EXPECTED_HASHES

    for record in records:
        data = record.to_dict()
        assert data["schema_version"] == "source_reference_intake_v1"
        assert data["reference_only"] is True
        assert data["code_copying_allowed"] is False
        assert data["runtime_execution_allowed"] is False
        assert data["live_network_allowed"] is False
        assert data["credential_or_profile_use_allowed"] is False
        assert data["raw_source_included"] is False
        assert data["full_local_path_included"] is False
        assert data["supplied_name"].endswith(".zip")
        assert "copy_proprietary_or_minified_code" in data["prohibited_use"]
        assert "T:\\" not in json.dumps(data)
        assert "C:\\Users" not in json.dumps(data)


def test_reference_intake_records_preserve_rev4_and_extension_distinction() -> None:
    records = {record.pack_id: record for record in reference_pack_intake_records()}

    rev4 = records["rev4_site_capture_preparation_pack"]
    assert rev4.kind is ReferencePackKind.REV4_PREPARATION_PACK
    assert ReferenceUseBoundary.LOCAL_FIXTURE_GUIDANCE in rev4.allowed_use
    assert "localhost_fixture_first_test_matrix" in rev4.architecture_patterns

    extension_two = records["extension_reference_2_mv3_offscreen_managed_schema"]
    assert extension_two.kind is ReferencePackKind.BROWSER_EXTENSION_REFERENCE
    assert "manifest_v3_service_worker" in extension_two.architecture_patterns
    assert "offscreen_document_for_background_tasks" in extension_two.architecture_patterns
    assert (
        ReferenceUseBoundary.LICENCE_SECURITY_REVIEW_REQUIRED
        in extension_two.allowed_use
    )

    extension_three = records["extension_reference_3_pdf_capture_style_surface"]
    assert "native_messaging_permission_surface" in extension_three.architecture_patterns
    assert "downloads_and_file_system_permission_surface" in extension_three.architecture_patterns
    assert any("not_reused" in note for note in extension_three.security_notes)


def test_reference_intake_summary_is_stable_counts_only() -> None:
    records = reference_pack_intake_records()
    summary = build_reference_pack_intake_summary(records)
    repeated = build_reference_pack_intake_summary(tuple(reversed(records)))

    assert summary == repeated
    data = summary.to_dict()
    assert data["summary_id"].startswith("source_reference_intake_")
    assert data["status"] == "REFERENCE_INTAKE_RECORDED"
    assert data["record_count"] == 4
    assert data["architecture_pattern_count"] >= 18
    assert data["reference_only"] is True
    assert data["code_copying_allowed"] is False
    assert data["runtime_execution_allowed"] is False
    assert data["live_network_allowed"] is False
    assert data["credential_or_profile_use_allowed"] is False
    assert data["raw_source_included"] is False
    assert data["full_local_path_included"] is False
    assert data["licence_security_review_required"] is True

    rendered_json = reference_pack_intake_summary_to_json(summary)
    rendered_text = build_reference_pack_intake_summary_text(summary)
    assert "Source reference intake summary" in rendered_text
    assert "Reference packs: 4" in rendered_text
    assert "Code copying allowed: false" in rendered_text
    assert "Runtime execution allowed: false" in rendered_text
    assert "T:\\" not in rendered_json
    assert "C:\\Users" not in rendered_json


def test_reference_intake_validation_rejects_unsafe_reuse_claims() -> None:
    base = reference_pack_intake_records()[0]
    unsafe_cases = (
        ReferencePackIntakeRecord(**{**base.__dict__, "pack_id": "bad-code-copy", "code_copying_allowed": True}),
        ReferencePackIntakeRecord(**{**base.__dict__, "pack_id": "bad-runtime", "runtime_execution_allowed": True}),
        ReferencePackIntakeRecord(**{**base.__dict__, "pack_id": "bad-network", "live_network_allowed": True}),
        ReferencePackIntakeRecord(**{**base.__dict__, "pack_id": "bad-profile", "credential_or_profile_use_allowed": True}),
        ReferencePackIntakeRecord(**{**base.__dict__, "pack_id": "bad-source", "raw_source_included": True}),
        ReferencePackIntakeRecord(**{**base.__dict__, "pack_id": "bad-path", "full_local_path_included": True}),
    )

    for record in unsafe_cases:
        try:
            validate_reference_pack_intake_records((record,))
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe record should fail: {record.pack_id}")


def test_reference_record_json_does_not_include_code_or_paths() -> None:
    rendered = "\n".join(
        reference_pack_intake_record_to_json(record)
        for record in reference_pack_intake_records()
    )

    for unsafe_text in (
        "function(",
        "chrome.",
        "browser.",
        "service-worker.js\\n",
        "background.js\\n",
        "C:\\Users",
        "T:\\",
        "cookie value",
        "api key",
        "token value",
        "copied source",
    ):
        assert unsafe_text not in rendered


def run_self_test() -> None:
    test_reference_pack_records_are_deterministic_and_reference_only()
    test_reference_intake_records_preserve_rev4_and_extension_distinction()
    test_reference_intake_summary_is_stable_counts_only()
    test_reference_intake_validation_rejects_unsafe_reuse_claims()
    test_reference_record_json_does_not_include_code_or_paths()


if __name__ == "__main__":
    run_self_test()
    print("Source reference intake self-test passed.")
