import json
from pathlib import Path
from tempfile import TemporaryDirectory

from evidence_database_demo_fixture import build_synthetic_evidence_database_demo_fixture
from evidence_database_review_io import (
    EVIDENCE_DATABASE_REVIEW_EXPORT_SCHEMA_VERSION,
    build_evidence_database_review_export_payload,
    evidence_database_review_export_json,
    import_evidence_database_review_export_payload,
    read_evidence_database_review_export_file,
    validate_evidence_database_review_export_payload,
    write_evidence_database_review_export_file,
)


def run_self_test() -> None:
    fixture = build_synthetic_evidence_database_demo_fixture()
    payload = build_evidence_database_review_export_payload(
        session=fixture.session,
        preview_request=fixture.preview_request,
        preview_result=fixture.preview_result,
        decisions=fixture.decisions,
        apply_plan=fixture.apply_plan,
        roots=(fixture.root,),
        taxonomy_versions=(fixture.taxonomy_version,),
        records=fixture.records,
        export_id="synthetic_demo_export",
    )
    assert payload["schema_version"] == EVIDENCE_DATABASE_REVIEW_EXPORT_SCHEMA_VERSION
    assert payload["export_id"] == "synthetic_demo_export"
    assert len(payload["payload_sha256"]) == 64
    assert payload == build_evidence_database_review_export_payload(
        session=fixture.session,
        preview_request=fixture.preview_request,
        preview_result=fixture.preview_result,
        decisions=fixture.decisions,
        apply_plan=fixture.apply_plan,
        roots=(fixture.root,),
        taxonomy_versions=(fixture.taxonomy_version,),
        records=fixture.records,
        export_id="synthetic_demo_export",
    )
    assert payload["session"]["dry_run_only"] is True
    assert payload["preview_request"]["supplied_records_only"] is True
    assert payload["preview_request"]["broad_scan_requested"] is False
    assert payload["preview_result"]["broad_scan_performed"] is False
    assert payload["preview_result"]["file_operation_performed"] is False
    assert payload["apply_plan"]["dry_run"] is True
    assert payload["apply_plan"]["execute_file_moves"] is False
    assert payload["apply_plan"]["execute_classification_changes"] is False
    assert payload["apply_plan"]["file_operation_performed"] is False
    assert payload["apply_plan"]["destructive_action_not_implemented"] is True
    assert len(payload["decisions"]) == 3
    assert len(payload["index_manifest"]["records"]) == 6

    export_text = evidence_database_review_export_json(payload)
    assert export_text.endswith("\n")
    loaded = json.loads(export_text)
    assert loaded == payload
    assert validate_evidence_database_review_export_payload(loaded) == ()
    imported = import_evidence_database_review_export_payload(loaded)
    assert imported.ok is True
    assert imported.errors == ()
    assert imported.bundle is not None
    assert imported.bundle.payload_sha256 == payload["payload_sha256"]
    assert imported.bundle.session.session_id == fixture.session.session_id
    assert imported.bundle.preview_request.supplied_records_only is True
    assert imported.bundle.preview_request.broad_scan_requested is False
    assert imported.bundle.preview_result.record_count == 6
    assert imported.bundle.preview_result.broad_scan_performed is False
    assert imported.bundle.preview_result.file_operation_performed is False
    assert len(imported.bundle.decisions) == 3
    assert imported.bundle.apply_plan.dry_run is True
    assert imported.bundle.apply_plan.execute_file_moves is False
    assert imported.bundle.apply_plan.execute_classification_changes is False
    assert imported.bundle.apply_plan.file_operation_performed is False
    assert imported.bundle.apply_plan.destructive_action_not_implemented is True
    assert all(
        entry.file_operation_performed is False
        for entry in imported.bundle.apply_plan.entries
    )
    assert all(
        entry.classification_change_executed is False
        for entry in imported.bundle.apply_plan.entries
    )
    assert len(imported.bundle.index_manifest.records) == 6
    lowered = export_text.lower()
    assert "synthetic_fixture/evidence_demo" in export_text
    assert "example.test/evidence-demo" in export_text
    assert "c:/users" not in lowered
    assert "t:/references" not in lowered
    assert "api_key" not in lowered
    assert "authorization" not in lowered
    assert "cookie" not in lowered

    with TemporaryDirectory() as temp_dir:
        export_path = Path(temp_dir) / "review_session_export.json"
        result = write_evidence_database_review_export_file(
            export_path=str(export_path),
            session=fixture.session,
            preview_request=fixture.preview_request,
            preview_result=fixture.preview_result,
            decisions=fixture.decisions,
            apply_plan=fixture.apply_plan,
            roots=(fixture.root,),
            taxonomy_versions=(fixture.taxonomy_version,),
            records=fixture.records,
            export_id="synthetic_demo_export",
        )
        assert result.export_path == str(export_path)
        assert result.payload_sha256 == payload["payload_sha256"]
        assert result.byte_count == len(export_text.encode("utf-8"))
        assert export_path.read_text(encoding="utf-8") == export_text
        imported_file = read_evidence_database_review_export_file(str(export_path))
        assert imported_file.ok is True
        assert imported_file.bundle is not None
        assert imported_file.bundle.payload_sha256 == payload["payload_sha256"]
        assert sorted(path.name for path in Path(temp_dir).iterdir()) == [
            "review_session_export.json"
        ]

        malformed_path = Path(temp_dir) / "malformed.json"
        malformed_path.write_text("{not valid", encoding="utf-8")
        malformed = read_evidence_database_review_export_file(str(malformed_path))
        assert malformed.ok is False
        assert malformed.errors == ("read_or_json_parse_failed",)

    destructive_payload = json.loads(export_text)
    destructive_payload["apply_plan"]["execute_file_moves"] = True
    assert "apply_plan_execute_file_moves" in validate_evidence_database_review_export_payload(
        destructive_payload
    )
    destructive_import = import_evidence_database_review_export_payload(destructive_payload)
    assert destructive_import.ok is False
    assert destructive_import.bundle is None
    assert "payload_sha256_mismatch" in destructive_import.errors
    assert "apply_plan_execute_file_moves" in destructive_import.errors

    broad_scan_payload = json.loads(export_text)
    broad_scan_payload["preview_request"]["broad_scan_requested"] = True
    broad_scan_payload["session"]["broad_scan_allowed"] = True
    broad_scan_import = import_evidence_database_review_export_payload(broad_scan_payload)
    assert broad_scan_import.ok is False
    assert "session_broad_scan_allowed" in broad_scan_import.errors
    assert "preview_request_broad_scan_requested" in broad_scan_import.errors

    secret_key_payload = json.loads(export_text)
    secret_key_payload["authorization"] = "not-a-real-secret"
    secret_key_import = import_evidence_database_review_export_payload(secret_key_payload)
    assert secret_key_import.ok is False
    assert "secret_like_key_present" in secret_key_import.errors


if __name__ == "__main__":
    run_self_test()
    print("Evidence database review I/O self-test passed.")
