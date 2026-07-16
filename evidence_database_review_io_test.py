import json
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from evidence_database_demo_fixture import build_synthetic_evidence_database_demo_fixture
from evidence_database_index import stable_json_dumps
from evidence_database_review_io import (
    EVIDENCE_DATABASE_REVIEW_EXPORT_SCHEMA_VERSION,
    build_evidence_database_review_export_payload,
    evidence_database_review_export_json,
    import_evidence_database_review_export_payload,
    read_evidence_database_review_export_file,
    validate_evidence_database_review_export_payload,
    write_evidence_database_review_export_file,
)


def _rehash_payload(payload: dict[str, object]) -> dict[str, object]:
    updated = dict(payload)
    without_hash = dict(updated)
    without_hash.pop("payload_sha256", None)
    updated["payload_sha256"] = hashlib.sha256(
        stable_json_dumps(without_hash).encode("utf-8")
    ).hexdigest()
    return updated


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

    schema_payload = json.loads(export_text)
    schema_payload["schema_version"] = "evidence-database-review-export-v0"
    schema_payload = _rehash_payload(schema_payload)
    schema_import = import_evidence_database_review_export_payload(schema_payload)
    assert schema_import.ok is False
    assert schema_import.errors == ("unsupported_schema_version",)

    missing_hash_payload = json.loads(export_text)
    missing_hash_payload.pop("payload_sha256")
    missing_hash_import = import_evidence_database_review_export_payload(
        missing_hash_payload
    )
    assert missing_hash_import.ok is False
    assert "payload_sha256_mismatch" in missing_hash_import.errors

    incorrect_hash_payload = json.loads(export_text)
    incorrect_hash_payload["payload_sha256"] = "0" * 64
    incorrect_hash_import = import_evidence_database_review_export_payload(
        incorrect_hash_payload
    )
    assert incorrect_hash_import.ok is False
    assert incorrect_hash_import.errors == ("payload_sha256_mismatch",)

    compatible_extra_payload = json.loads(export_text)
    compatible_extra_payload["future_notes"] = {
        "ignored_by_current_importer": True,
        "fixture_note": "fixture-only",
    }
    compatible_extra_payload = _rehash_payload(compatible_extra_payload)
    compatible_extra_import = import_evidence_database_review_export_payload(
        compatible_extra_payload
    )
    assert compatible_extra_import.ok is True
    assert compatible_extra_import.bundle is not None
    assert compatible_extra_import.bundle.preview_result.record_count == 6

    malformed_record_payload = json.loads(export_text)
    malformed_record_payload["index_manifest"]["records"][0]["identity"] = {}
    malformed_record_payload = _rehash_payload(malformed_record_payload)
    malformed_record_import = import_evidence_database_review_export_payload(
        malformed_record_payload
    )
    assert malformed_record_import.ok is False
    assert "index_record_missing_item_id" in malformed_record_import.errors

    malformed_state_payload = json.loads(export_text)
    malformed_state_payload["index_manifest"]["records"][0]["classification_state"] = []
    malformed_state_payload = _rehash_payload(malformed_state_payload)
    malformed_state_import = import_evidence_database_review_export_payload(
        malformed_state_payload
    )
    assert malformed_state_import.ok is False
    assert "index_record_classification_state_not_object" in malformed_state_import.errors

    nested_secret_payload = json.loads(export_text)
    nested_secret_payload["index_manifest"]["records"][0]["identity"][
        "api_key"
    ] = "not-a-real-key"
    nested_secret_payload = _rehash_payload(nested_secret_payload)
    nested_secret_import = import_evidence_database_review_export_payload(
        nested_secret_payload
    )
    assert nested_secret_import.ok is False
    assert nested_secret_import.errors == ("secret_like_key_present",)


if __name__ == "__main__":
    run_self_test()
    print("Evidence database review I/O self-test passed.")
