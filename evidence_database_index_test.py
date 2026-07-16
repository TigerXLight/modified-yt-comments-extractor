from evidence_database_index import (
    CLASSIFICATION_NOT_EVIDENCED,
    CLASSIFICATION_PROPOSED,
    CLASSIFICATION_UNKNOWN,
    CLASSIFICATION_USER_CONFIRMED,
    EVIDENCE_DATABASE_INDEX_SCOPE,
    EvidenceBasis,
    EvidenceClassificationState,
    EvidenceClassificationValue,
    EvidenceDatabaseRoot,
    EvidenceIndexManifest,
    EvidenceIndexRecord,
    EvidenceItemIdentity,
    EvidencePathRecord,
    EvidencePlacementProposal,
    EvidenceReclassificationProposal,
    EvidenceTaxonomyVersion,
    append_or_update_evidence_index_record,
    build_classification_state,
    build_dry_run_proposal_result,
    build_evidence_basis,
    build_evidence_item_identity,
    build_placement_proposal,
    build_reclassification_proposal,
    evidence_index_manifest_with_hash,
    evidence_index_payload_sha256,
    read_evidence_index_file,
    stable_evidence_id,
    stable_json_dumps,
    write_evidence_index_file_atomic,
)
from evidence_schema import PrimarySourceStatus, SourceRole
from pathlib import Path
from tempfile import TemporaryDirectory


def _assert_timestamp(value: str) -> None:
    assert value.endswith("Z"), value
    assert "T" in value, value


def run_self_test() -> None:
    assert [item.value for item in EvidenceClassificationValue] == [
        "unknown",
        "not_evidenced",
        "user_confirmed",
        "proposed",
        "rejected",
        "superseded",
    ]
    assert CLASSIFICATION_UNKNOWN == "unknown"
    assert CLASSIFICATION_NOT_EVIDENCED == "not_evidenced"
    assert CLASSIFICATION_USER_CONFIRMED == "user_confirmed"
    assert CLASSIFICATION_PROPOSED == "proposed"

    stable_a = stable_evidence_id("edi", "https://example.test/a", r"C:\Root\File.txt")
    stable_b = stable_evidence_id("edi", "https://example.test/a", "C:/Root/File.txt")
    stable_c = stable_evidence_id("edi", "https://example.test/b", r"C:\Root\File.txt")
    assert stable_a == stable_b
    assert stable_a != stable_c
    assert stable_a.startswith("edi_")

    root = EvidenceDatabaseRoot(
        root_id=stable_evidence_id("root", "T:/Evidence"),
        root_path="T:/Evidence",
        label="Local evidence",
        taxonomy_version_id="taxonomy_user_v1",
    )
    assert root.dry_run_required is True
    assert root.moves_require_explicit_approval is True
    assert root.broad_scan_allowed is False
    assert "no broad folder scanning" in root.scope
    _assert_timestamp(root.registered_at_utc)

    taxonomy = EvidenceTaxonomyVersion(
        taxonomy_version_id="taxonomy_user_v1",
        label="User taxonomy",
        dimension_order=("topic", "directness", "month", "source_outlet"),
    )
    taxonomy_dict = taxonomy.to_dict()
    assert taxonomy_dict["dimension_order"] == [
        "topic",
        "directness",
        "month",
        "source_outlet",
    ]
    assert "religion_identity_status" in taxonomy_dict["sensitive_dimensions"]

    identity = build_evidence_item_identity(
        display_name="Example Article",
        source_url="https://example.test/article",
        local_path_hint="Topic/Indirect/2026-06/Outlet/Example Article",
        export_package_id="package-1",
        manifest_path="package-1/package-1_manifest.json",
        queue_item_id="queue-1",
        source_row_id="source-row-1",
    )
    assert isinstance(identity, EvidenceItemIdentity)
    assert identity.item_id == build_evidence_item_identity(
        display_name="Example Article",
        source_url="https://example.test/article",
        local_path_hint="Topic/Indirect/2026-06/Outlet/Example Article",
        export_package_id="package-1",
        manifest_path="package-1/package-1_manifest.json",
        queue_item_id="queue-1",
        source_row_id="source-row-1",
    ).item_id
    assert identity.source_url == "https://example.test/article"

    path = EvidencePathRecord(
        path_record_id=stable_evidence_id("path", identity.item_id, "current"),
        item_id=identity.item_id,
        current_path="Topic/Indirect/2026-06/Outlet/Example Article",
        previous_path="",
        proposed_path="Topic/Indirect/2026-06/Example Outlet/Example Article",
        history_note="Dry-run normalization only.",
    )
    assert path.file_operation_performed is False
    assert path.to_dict()["proposed_path"].endswith("Example Article")

    classification = EvidenceClassificationState(
        classification_value=EvidenceClassificationValue.UNKNOWN,
        dimensions={
            "religion_identity_status": "not identified",
            "source_outlet": "Outlet",
        },
        sensitive_dimensions_present=("religion_identity_status",),
    )
    classification_dict = classification.to_dict()
    assert classification_dict["classification_value"] == "unknown"
    assert classification_dict["weak_inference_prohibited"] is True
    assert classification_dict["user_confirmation_required"] is True

    basis = EvidenceBasis(
        basis_id=stable_evidence_id("basis", identity.item_id, "manual-note"),
        item_id=identity.item_id,
        basis_type="manual_source_note",
        source_url="https://example.test/article",
        source_role=SourceRole.SECONDARY_OUTSIDE_PERSPECTIVE,
        source_status=PrimarySourceStatus.SECONDARY_FRAMING_ONLY,
        evidence_text="User-entered note; not inferred from name or appearance.",
        confidence="user_supplied",
    )
    basis_dict = basis.to_dict()
    assert basis_dict["source_role"] == "SECONDARY_OUTSIDE_PERSPECTIVE"
    assert basis_dict["source_status"] == "SECONDARY_FRAMING_ONLY"
    assert basis_dict["sensitive_basis_confirmed"] is False

    placement = EvidencePlacementProposal(
        proposal_id=stable_evidence_id("place", identity.item_id, path.proposed_path),
        item_id=identity.item_id,
        database_root_id=root.root_id,
        current_path=path.current_path,
        proposed_path=path.proposed_path,
        basis_ids=(basis.basis_id,),
        reason="Outlet-name normalization suggestion.",
    )
    assert placement.file_operation_performed is False
    assert placement.user_confirmation_required is True

    proposed_classification = EvidenceClassificationState(
        classification_value=EvidenceClassificationValue.PROPOSED,
        dimensions={"source_outlet": "Example Outlet"},
        user_confirmed=False,
        source_evidenced=True,
    )
    reclass = EvidenceReclassificationProposal(
        proposal_id=stable_evidence_id("reclass", identity.item_id, "source_outlet"),
        item_id=identity.item_id,
        previous_path=path.current_path,
        proposed_path=path.proposed_path,
        previous_classification=classification,
        proposed_classification=proposed_classification,
        basis_ids=(basis.basis_id,),
        reason="Dry-run outlet label change.",
    )
    assert reclass.old_new_path_history_preserved is True
    assert reclass.file_operation_performed is False
    assert reclass.to_dict()["proposed_classification"]["classification_value"] == "proposed"

    record = EvidenceIndexRecord(
        identity=identity,
        database_root_id=root.root_id,
        taxonomy_version_id=taxonomy.taxonomy_version_id,
        path_records=(path,),
        classification_state=classification,
        evidence_basis=(basis,),
        placement_proposals=(placement,),
        reclassification_proposals=(reclass,),
    )
    record_dict = record.to_dict()
    assert record_dict["identity"]["item_id"] == identity.item_id
    assert record_dict["path_records"][0]["file_operation_performed"] is False
    assert record_dict["classification_state"]["dimensions"]["source_outlet"] == "Outlet"
    _assert_timestamp(record.created_at_utc)
    _assert_timestamp(record.updated_at_utc)

    manifest = EvidenceIndexManifest(
        manifest_id=stable_evidence_id("manifest", root.root_id, taxonomy.taxonomy_version_id),
        database_roots=(root,),
        taxonomy_versions=(taxonomy,),
        records=(record,),
    )
    manifest_hash = evidence_index_payload_sha256(manifest)
    hashed = evidence_index_manifest_with_hash(manifest)
    manifest_dict = hashed.to_dict()
    assert manifest_hash == hashed.payload_sha256
    assert len(manifest_hash) == 64
    assert manifest_dict["database_root_count"] == 1
    assert manifest_dict["taxonomy_version_count"] == 1
    assert manifest_dict["record_count"] == 1
    assert manifest_dict["payload_sha256"] == manifest_hash
    assert "no file movement" in manifest_dict["scope"]

    rendered = stable_json_dumps(hashed.to_dict())
    assert rendered == stable_json_dumps(hashed.to_dict())
    assert "requests" not in rendered
    assert "selenium" not in rendered
    assert "scan(" not in rendered
    assert "move(" not in rendered

    with TemporaryDirectory() as temp_dir:
        index_path = Path(temp_dir) / "evidence_index.json"
        missing = read_evidence_index_file(str(index_path))
        assert missing.status == "missing"
        assert missing.ok is False
        assert missing.errors == ("index_file_missing",)

        write_result = write_evidence_index_file_atomic(manifest, str(index_path))
        assert write_result.ok is True
        assert write_result.status == "ok"
        assert write_result.payload_sha256 == manifest_hash
        assert index_path.is_file()
        assert not index_path.with_name(".evidence_index.json.tmp").exists()

        loaded = read_evidence_index_file(str(index_path))
        assert loaded.ok is True
        assert loaded.manifest is not None
        assert loaded.manifest.manifest_id == manifest.manifest_id
        assert loaded.manifest.payload_sha256 == manifest_hash
        assert loaded.manifest.records[0].identity.item_id == identity.item_id
        assert loaded.to_dict()["ok"] is True
        assert "manifest" not in loaded.to_dict()

        second_identity = build_evidence_item_identity(
            display_name="Second Article",
            source_url="https://example.test/second",
        )
        second_record = EvidenceIndexRecord(identity=second_identity)
        appended = append_or_update_evidence_index_record(manifest, second_record)
        assert [item.identity.item_id for item in appended.records] == [
            identity.item_id,
            second_identity.item_id,
        ]
        updated_record = EvidenceIndexRecord(
            identity=identity,
            classification_state=EvidenceClassificationState(
                classification_value=EvidenceClassificationValue.USER_CONFIRMED,
                dimensions={"source_outlet": "Example Outlet"},
                user_confirmed=True,
                source_evidenced=True,
                user_confirmation_required=False,
            ),
        )
        updated = append_or_update_evidence_index_record(appended, updated_record)
        assert len(updated.records) == 2
        assert updated.records[0].classification_state.classification_value == (
            EvidenceClassificationValue.USER_CONFIRMED
        )

        bad_path = Path(temp_dir) / "bad.json"
        bad_path.write_text("{not-json", encoding="utf-8")
        bad = read_evidence_index_file(str(bad_path))
        assert bad.status == "invalid"
        assert bad.errors[0].startswith("index_read_failed:")

        before_failure = index_path.read_text(encoding="utf-8")

        def failing_replace(_src: str, _dst: str) -> None:
            raise OSError("simulated replace failure")

        failed_write = write_evidence_index_file_atomic(
            updated,
            str(index_path),
            replace_func=failing_replace,
        )
        assert failed_write.status == "write_failed"
        assert failed_write.ok is False
        assert failed_write.errors == ("index_write_failed:OSError",)
        assert index_path.read_text(encoding="utf-8") == before_failure
        assert not index_path.with_name(".evidence_index.json.tmp").exists()

    weak_sensitive = build_classification_state(
        classification_value=EvidenceClassificationValue.PROPOSED,
        dimensions={"religion_identity_status": "known from weak clue"},
        sensitive_dimensions_present=("religion_identity_status",),
        source_evidenced=False,
        user_confirmed=False,
    )
    assert weak_sensitive.classification_value is EvidenceClassificationValue.UNKNOWN
    assert weak_sensitive.user_confirmation_required is True
    assert weak_sensitive.weak_inference_prohibited is True
    assert "explicit evidence" in weak_sensitive.notes

    evidenced_sensitive = build_classification_state(
        classification_value=EvidenceClassificationValue.PROPOSED,
        dimensions={"religion_identity_status": "explicitly stated"},
        sensitive_dimensions_present=("religion_identity_status",),
        source_evidenced=True,
        user_confirmed=False,
    )
    assert evidenced_sensitive.classification_value is EvidenceClassificationValue.PROPOSED
    assert evidenced_sensitive.source_evidenced is True

    confirmed = build_classification_state(
        classification_value=EvidenceClassificationValue.USER_CONFIRMED,
        dimensions={"source_outlet": "Example Outlet"},
        user_confirmed=True,
    )
    assert confirmed.classification_value is EvidenceClassificationValue.USER_CONFIRMED
    assert confirmed.user_confirmation_required is False

    not_evidenced = build_classification_state(
        classification_value=EvidenceClassificationValue.NOT_EVIDENCED,
        dimensions={"relationship_category": "not evidenced"},
    )
    assert not_evidenced.classification_value is EvidenceClassificationValue.NOT_EVIDENCED

    rejected = build_classification_state(
        classification_value=EvidenceClassificationValue.REJECTED,
        dimensions={"source_outlet": "Rejected outlet proposal"},
    )
    assert rejected.classification_value is EvidenceClassificationValue.REJECTED

    superseded = build_classification_state(
        classification_value=EvidenceClassificationValue.SUPERSEDED,
        dimensions={"source_outlet": "Old outlet label"},
    )
    assert superseded.classification_value is EvidenceClassificationValue.SUPERSEDED

    generated_basis = build_evidence_basis(
        item_id=identity.item_id,
        basis_type="source_metadata",
        source_url=identity.source_url,
        source_role=SourceRole.SECONDARY_OUTSIDE_PERSPECTIVE,
        source_status=PrimarySourceStatus.SECONDARY_FRAMING_ONLY,
        evidence_text="Outlet label appears in supplied metadata.",
        confidence="metadata_explicit",
    )
    assert generated_basis.basis_id == build_evidence_basis(
        item_id=identity.item_id,
        basis_type="source_metadata",
        source_url=identity.source_url,
        source_role=SourceRole.SECONDARY_OUTSIDE_PERSPECTIVE,
        source_status=PrimarySourceStatus.SECONDARY_FRAMING_ONLY,
        evidence_text="Outlet label appears in supplied metadata.",
        confidence="metadata_explicit",
    ).basis_id

    generated_placement = build_placement_proposal(
        item_id=identity.item_id,
        database_root_id=root.root_id,
        current_path=path.current_path,
        proposed_path=path.proposed_path,
        basis_ids=(generated_basis.basis_id,),
        reason="Explicit metadata supports source outlet label.",
        confidence="metadata_explicit",
    )
    assert generated_placement.file_operation_performed is False
    assert generated_placement.status == "dry_run"

    generated_reclassification = build_reclassification_proposal(
        item_id=identity.item_id,
        previous_path=path.current_path,
        proposed_path=path.proposed_path,
        previous_classification=classification,
        proposed_classification=evidenced_sensitive,
        basis_ids=(generated_basis.basis_id,),
        reason="Explicit source evidence supports a reviewable change.",
    )
    assert generated_reclassification.file_operation_performed is False
    assert generated_reclassification.old_new_path_history_preserved is True
    assert generated_reclassification.status == "user_confirmation_required"

    dry_run = build_dry_run_proposal_result(
        identity=identity,
        database_root_id=root.root_id,
        current_path=path.current_path,
        proposed_path=path.proposed_path,
        dimensions={"source_outlet": "Example Outlet"},
        basis=generated_basis,
        previous_classification=classification,
        source_evidenced=True,
        reason="Explicit metadata supports source outlet label.",
        confidence="metadata_explicit",
    )
    assert dry_run.no_files_moved is True
    assert dry_run.placement_proposal is not None
    assert dry_run.placement_proposal.file_operation_performed is False
    assert dry_run.reclassification_proposal is not None
    assert dry_run.reclassification_proposal.file_operation_performed is False
    assert dry_run.classification_state.classification_value is EvidenceClassificationValue.PROPOSED
    assert dry_run.to_dict()["no_files_moved"] is True

    unsafe_dry_run = build_dry_run_proposal_result(
        identity=identity,
        database_root_id=root.root_id,
        current_path=path.current_path,
        proposed_path=path.proposed_path,
        dimensions={"religion_identity_status": "guessed from weak clue"},
        basis=generated_basis,
        previous_classification=classification,
        sensitive_dimensions_present=("religion_identity_status",),
        source_evidenced=False,
        user_confirmed=False,
        reason="Weak clue must not classify sensitive identity.",
    )
    assert unsafe_dry_run.classification_state.classification_value is (
        EvidenceClassificationValue.UNKNOWN
    )
    assert unsafe_dry_run.warnings == (
        "sensitive_classification_requires_explicit_evidence_or_user_confirmation",
    )
    assert unsafe_dry_run.no_files_moved is True


if __name__ == "__main__":
    run_self_test()
    print("Evidence database index self-test passed.")
