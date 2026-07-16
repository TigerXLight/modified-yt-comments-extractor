import json
from pathlib import Path
from tempfile import TemporaryDirectory

from evidence_database_demo_fixture import build_synthetic_evidence_database_demo_fixture
from evidence_database_review_io import (
    EVIDENCE_DATABASE_REVIEW_EXPORT_SCHEMA_VERSION,
    build_evidence_database_review_export_payload,
    evidence_database_review_export_json,
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
        assert sorted(path.name for path in Path(temp_dir).iterdir()) == [
            "review_session_export.json"
        ]


if __name__ == "__main__":
    run_self_test()
    print("Evidence database review I/O self-test passed.")
