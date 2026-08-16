from pathlib import Path
from tempfile import TemporaryDirectory

from profile_media_database import (
    ClaimBasis,
    CurrentnessStatus,
    MediaBucket,
    MediaOrigin,
    MovePlanStatus,
    AuditEventType,
    FolderOperationStatus,
    ReviewItemStatus,
    ReviewItemType,
    ProfileMediaReviewItem,
    apply_folder_operation,
    build_audit_event_for_folder_operation_result,
    build_audit_event_for_review_decision,
    build_folder_operation_from_review_item,
    build_folder_operations_from_review_queue,
    build_review_items_from_case_repository_path_plan,
    build_review_queue,
    mark_review_item_decision,
    ProfileCollectionLevel,
    ProfileSourceRole,
    build_case_folder_layout,
    build_case_local_profile_from_text,
    build_case_record,
    build_case_record_from_repository_plan,
    build_case_repository_classification,
    build_case_repository_path,
    build_global_profiles_path,
    build_global_profile_from_case_profile,
    build_manifest,
    build_media_source_record,
    plan_case_repository_location,
    build_media_source_record_from_import_plan,
    build_source_claim_evaluation,
    build_profile_record,
    normalize_media_bucket,
    parse_profile_text_blocks,
    plan_folder_move,
    plan_media_import,
    build_database_tree_rows,
    render_database_tree_text,
    write_database_tree_text,
    write_manifest_json,
    read_json_payload,
)


def run_self_test() -> None:
    database_root = r"T:\Database"
    case_root = r"T:\Database\Sexual or Gender based\Female upon Male\Actions\June 2026\BelfastLive\June 2026 - Murderous wife said husband died by falling onto a little knife - White"
    layout = build_case_folder_layout(case_root)
    assert layout.case_profiles_path.replace("/", "\\").endswith(r"\Profiles")
    assert layout.people_path.replace("/", "\\").endswith(r"\People")
    assert layout.sources_path.replace("/", "\\").endswith(r"\Sources")
    assert layout.articles_path.replace("/", "\\").endswith(r"\Sources\Articles")
    assert layout.social_media_offline_path.replace("/", "\\").endswith(r"\Sources\Social Media\Offline")
    assert layout.social_media_online_path.replace("/", "\\").endswith(r"\Sources\Social Media\Online")
    assert layout.internal_media_path.replace("/", "\\").endswith(r"\Sources\Internal Media")
    assert layout.reference_extants_path.replace("/", "\\").endswith(r"\Reference Extants")
    assert layout.file_move_performed is False
    assert layout.folder_creation_performed is False

    assert build_global_profiles_path(database_root).replace("/", "\\").endswith(r"\Profiles")

    text = """
Name: Example Person
Date: 2026-06-05
Text: A source-authored statement about the person's own experience.
Identifiers:
Description: blue coat
Religion: source-stated Muslim
Address: T:\\Case\\Sources\\Articles\\article.txt
Source: BelfastLive article
----
Date: 2026-06-06
Text: Case-only source note without a person name.
Identifiers: Clothing: dark jacket; Associations: named place
Address: T:\\Case\\Sources\\Social Media\\Online\\post.txt
Source: Social Media
""".strip()
    blocks = parse_profile_text_blocks(
        text,
        default_source_bucket=MediaBucket.ARTICLES.value,
        default_source_role=ProfileSourceRole.PRIMARY_SELF_AUTHORED_SCOPE,
        default_claim_basis=ClaimBasis.SELF_AUTHORED_EXPERIENCE,
        default_currentness_status=CurrentnessStatus.CURRENT,
    )
    assert len(blocks) == 2
    assert blocks[0].name == "Example Person"
    assert blocks[0].source_page == "BelfastLive article"
    assert "Religion: source-stated Muslim" in blocks[0].identifiers
    assert blocks[1].name == ""
    assert blocks[1].source_page == "Social Media"

    global_profile = build_profile_record(
        canonical_name="Example Person",
        text_blocks=(blocks[0],),
        collection_level=ProfileCollectionLevel.GLOBAL_HEADER_PROFILES,
    )
    case_profile = build_profile_record(
        canonical_name="Example Person",
        text_blocks=blocks,
        collection_level=ProfileCollectionLevel.CASE_LOCAL_PROFILES,
        case_id="case_1",
    )
    assert global_profile.collection_level == ProfileCollectionLevel.GLOBAL_HEADER_PROFILES
    assert case_profile.collection_level == ProfileCollectionLevel.CASE_LOCAL_PROFILES
    assert case_profile.identifiers[1].sensitive_identifier is True
    assert case_profile.identifiers[1].source_evidenced_only is True
    assert case_profile.identifiers[1].weak_inference_prohibited is True

    media_source = build_media_source_record(
        source_page="BelfastLive article",
        source_bucket=MediaBucket.ARTICLES,
        local_address=r"T:\Case\Sources\Articles\article.txt",
        title="June 2026 - example title",
        source_role=ProfileSourceRole.TERTIARY_PROPAGATED_SOURCE,
        claim_basis=ClaimBasis.AGENCY_OR_OUTSIDE_RETELLING,
    )
    case = build_case_record(
        database_root=database_root,
        case_title="June 2026 - example case",
        profiles=(case_profile,),
        media_sources=(media_source,),
        case_id="case_1",
        case_root=case_root,
    )
    manifest = build_manifest(
        database_root=database_root,
        cases=(case,),
        global_profiles=(global_profile,),
    )
    manifest_dict = manifest.to_dict()
    assert manifest_dict["schema_version"] == "profile-media-database-v75f"
    assert manifest_dict["case_count"] == 1
    assert manifest_dict["global_profile_count"] == 1
    assert manifest.payload_sha256

    evaluation = build_source_claim_evaluation(
        source_role=ProfileSourceRole.TERTIARY_PROPAGATED_SOURCE,
        claim_basis=ClaimBasis.AGENCY_OR_OUTSIDE_RETELLING,
        currentness_status=CurrentnessStatus.HISTORICAL,
        source_chain_gap=True,
        disputed_framing=True,
        notes_on_context_dispute="publisher framing disputed by original uploader",
        family_or_authority_claim_basis="authority claim basis recorded",
        identity_claim_basis="source-stated identity only",
        appearance_claim_basis="appearance claim not used for sensitive inference",
        collaboration_or_corroboration_notes="repeated reports need defined corroboration",
    )
    article_plan = plan_media_import(
        case_root=case_root,
        case_id="case_1",
        source_page="BelfastLive",
        source_bucket="Articles",
        source_title="June 2026 - article title",
        source_claim_evaluation=evaluation,
    )
    assert article_plan.media_origin == MediaOrigin.EXTERNAL_MEDIA
    assert article_plan.proposed_local_address.replace("/", "\\").endswith(r"\Sources\Articles\June 2026 - article title.txt")
    assert article_plan.folder_creation_performed is False
    assert article_plan.file_copy_performed is False
    assert article_plan.file_move_performed is False
    assert article_plan.source_claim_evaluation.source_chain_gap is True

    social_online_plan = plan_media_import(
        case_root=case_root,
        source_page="X post",
        source_bucket="Social Media/Online",
        source_filename="x-post.json",
        default_extension=".json",
    )
    assert social_online_plan.proposed_local_address.replace("/", "\\").endswith(r"\Sources\Social Media\Online\x-post.json")

    social_offline_plan = plan_media_import(
        case_root=case_root,
        source_page="USB scan",
        source_bucket="Social Media/Offline",
        source_filename="usb-scan.pdf",
        default_extension=".pdf",
    )
    assert social_offline_plan.proposed_local_address.replace("/", "\\").endswith(r"\Sources\Social Media\Offline\usb-scan.pdf")

    internal_plan = plan_media_import(
        case_root=case_root,
        source_page="creator note",
        source_bucket=MediaBucket.INTERNAL_MEDIA,
        source_filename="creator-note.txt",
    )
    assert internal_plan.media_origin == MediaOrigin.INTERNAL_MEDIA
    assert internal_plan.proposed_local_address.replace("/", "\\").endswith(r"\Sources\Internal Media\creator-note.txt")

    planned_source = build_media_source_record_from_import_plan(article_plan)
    assert planned_source.local_address == article_plan.proposed_local_address
    assert planned_source.source_claim_evaluation is not None
    assert planned_source.source_claim_evaluation.disputed_framing is True

    case_local_from_text = build_case_local_profile_from_text(
        case_id="case_2",
        text=text,
        default_source_bucket="Social Media/Online",
        default_source_role=ProfileSourceRole.SECONDARY_WITNESS_ACCOUNT,
        default_claim_basis=ClaimBasis.WITNESS_ACCOUNT,
    )
    assert case_local_from_text.collection_level == ProfileCollectionLevel.CASE_LOCAL_PROFILES
    assert case_local_from_text.case_id == "case_2"
    assert case_local_from_text.text_blocks[0].source_bucket == MediaBucket.SOCIAL_MEDIA_ONLINE.value
    global_from_case = build_global_profile_from_case_profile(case_local_from_text)
    assert global_from_case.collection_level == ProfileCollectionLevel.GLOBAL_HEADER_PROFILES
    assert global_from_case.case_id == ""

    assert normalize_media_bucket("social media offline") == MediaBucket.SOCIAL_MEDIA_OFFLINE
    assert normalize_media_bucket("Internal Media") == MediaBucket.INTERNAL_MEDIA

    move_plan = plan_folder_move(
        current_path=r"T:\Database\Unknown\Case",
        proposed_path=r"T:\Database\Religious Identity\Case",
        reason="later source-stated religion updated case placement",
        source_basis="BelfastLive article line/source note",
    )
    assert move_plan.status == MovePlanStatus.REVIEW_REQUIRED
    assert move_plan.file_move_performed is False
    assert move_plan.folder_creation_performed is False
    assert "no folder was moved" in move_plan.audit_note


    terrorism_classification = build_case_repository_classification(
        domain="Terrorism",
        conduct=("Actions", "Domestic", "Incitment", "Language", "Threat Fear"),
        religious_identity_bucket="Non-religious or not identified",
        date_bucket="June 2026",
        source_name="BelfastLive",
        case_title="June 2026 - Murderous wife said husband died by falling onto a little knife - White",
        source_basis="BelfastLive source folder claim evaluation",
        claim_basis=ClaimBasis.AGENCY_OR_OUTSIDE_RETELLING,
        source_role=ProfileSourceRole.TERTIARY_PROPAGATED_SOURCE,
    )
    terrorism_path = build_case_repository_path(database_root, terrorism_classification).replace("/", "\\")
    assert terrorism_path.endswith(
        r"\Terrorism\Actions\Domestic\Incitment\Language\Threat Fear\Non-religious or not identified\June 2026\BelfastLive\June 2026 - Murderous wife said husband died by falling onto a little knife - White"
    )
    assert terrorism_classification.sensitive_bucket_source_evidenced_only is True
    assert terrorism_classification.weak_sensitive_inference_prohibited is True

    case_path_plan = plan_case_repository_location(
        database_root=database_root,
        classification=terrorism_classification,
        current_case_root=r"T:\Database\Unclassified\Old Case Folder",
    )
    assert case_path_plan.proposed_case_root.replace("/", "\\") == terrorism_path
    assert case_path_plan.move_plan is not None
    assert case_path_plan.move_plan.file_move_performed is False
    assert case_path_plan.moved_or_renamed_folders is False
    assert case_path_plan.created_folders is False
    assert case_path_plan.layout.articles_path.replace("/", "\\").endswith(r"\Sources\Articles")

    same_path_plan = plan_case_repository_location(
        database_root=database_root,
        classification=terrorism_classification,
        current_case_root=case_path_plan.proposed_case_root,
    )
    assert same_path_plan.status == MovePlanStatus.NO_CHANGE
    assert same_path_plan.move_plan is None

    sensitive_classification_without_basis = build_case_repository_classification(
        domain="Rape",
        conduct=("Adults", "Direct"),
        religious_identity_bucket="Religious Identity",
        date_bucket="June 2026",
        source_name="Belfast Telegraph",
        case_title="5th Jun - example case",
    )
    assert "sensitive_repository_bucket_without_source_basis" in sensitive_classification_without_basis.warnings

    case_from_path = build_case_record_from_repository_plan(
        plan=case_path_plan,
        profiles=(case_profile,),
        media_sources=(media_source,),
    )
    assert case_from_path.case_root == case_path_plan.proposed_case_root
    assert case_from_path.layout.case_profiles_path.replace("/", "\\").endswith(r"\Profiles")


    review_items = build_review_items_from_case_repository_path_plan(case_path_plan)
    assert len(review_items) == 1
    review_item = review_items[0]
    assert review_item.status == ReviewItemStatus.PENDING_REVIEW
    assert review_item.file_move_performed is False
    assert review_item.folder_creation_performed is False
    assert review_item.current_path.replace("/", "\\").endswith(r"\Unclassified\Old Case Folder")
    assert review_item.proposed_path.replace("/", "\\") == terrorism_path
    assert "confirm_folder_rename_or_move_separately" in review_item.required_actions

    approved_review_item = mark_review_item_decision(
        review_item,
        approved=True,
        reviewer_note="manual review confirms source-basis path change only",
        reviewed_by="case creator",
    )
    assert approved_review_item.status == ReviewItemStatus.APPROVED_FOR_ACTION
    assert approved_review_item.user_confirmation_recorded is True
    assert approved_review_item.file_move_performed is False
    assert "no folder was created" in approved_review_item.audit_note

    warning_review_items = build_review_items_from_case_repository_path_plan(
        plan_case_repository_location(
            database_root=database_root,
            classification=sensitive_classification_without_basis,
            current_case_root=r"T:\Database\Rape\Adults\Direct\Old",
        )
    )
    assert any(item.reason == "sensitive_repository_bucket_without_source_basis" for item in warning_review_items)
    assert any(item.sensitive_review_required for item in warning_review_items)

    review_queue = build_review_queue((approved_review_item,))
    assert review_queue.to_dict()["item_count"] == 1
    assert review_queue.to_dict()["approved_count"] == 1

    audit_event = build_audit_event_for_review_decision(approved_review_item)
    assert audit_event.event_type == AuditEventType.REVIEW_DECISION_RECORDED
    assert audit_event.performed is False
    assert audit_event.file_move_performed is False

    dry_run_operation = build_folder_operation_from_review_item(approved_review_item)
    assert dry_run_operation.allowed_to_execute is False
    dry_run_result = apply_folder_operation(dry_run_operation)
    assert dry_run_result.status == FolderOperationStatus.PLANNED_DRY_RUN
    assert dry_run_result.performed is False
    assert dry_run_result.moved_or_renamed_folder is False
    assert "dry_run_only_no_filesystem_change_allowed" in dry_run_result.warnings

    blocked_operation = build_folder_operation_from_review_item(review_item, dry_run_only=False, allow_execute=True)
    blocked_result = apply_folder_operation(blocked_operation, execute=True)
    assert blocked_result.status == FolderOperationStatus.BLOCKED_REVIEW_NOT_APPROVED
    assert blocked_result.performed is False

    queued_operations = build_folder_operations_from_review_queue(review_queue)
    assert len(queued_operations) == 1
    assert queued_operations[0].review_id == approved_review_item.review_id

    with TemporaryDirectory() as temp_root:
        temp_path = Path(temp_root)
        source_case = temp_path / "Unclassified" / "Old Case Folder"
        source_case.mkdir(parents=True)
        (source_case / "marker.txt").write_text("case marker", encoding="utf-8")
        destination_case = temp_path / "Database" / "Terrorism" / "Case Folder"
        temp_review_item = mark_review_item_decision(
            ProfileMediaReviewItem(
                review_id="review_temp_move",
                item_type=ReviewItemType.FOLDER_MOVE,
                title="Temp reviewed move",
                case_id="case_temp",
                case_title="Case Folder",
                current_path=str(source_case),
                proposed_path=str(destination_case),
                reason="temporary reviewed test move",
                source_basis="test source basis",
            ),
            approved=True,
            reviewer_note="temporary test only",
            reviewed_by="test",
        )
        executable_operation = build_folder_operation_from_review_item(
            temp_review_item,
            dry_run_only=False,
            allow_execute=True,
        )
        missing_parent_result = apply_folder_operation(executable_operation, execute=True)
        assert missing_parent_result.status == FolderOperationStatus.BLOCKED_PARENT_MISSING
        applied_result = apply_folder_operation(executable_operation, execute=True, create_parent=True)
        assert applied_result.status == FolderOperationStatus.APPLIED
        assert applied_result.performed is True
        assert applied_result.moved_or_renamed_folder is True
        assert destination_case.exists()
        assert not source_case.exists()
        assert (destination_case / "marker.txt").read_text(encoding="utf-8") == "case marker"
        operation_audit = build_audit_event_for_folder_operation_result(executable_operation, applied_result)
        assert operation_audit.event_type == AuditEventType.FOLDER_OPERATION_APPLIED
        assert operation_audit.performed is True

    manifest_with_review = build_manifest(
        database_root=database_root,
        cases=(case_from_path,),
        global_profiles=(global_profile,),
        move_plans=(case_path_plan.move_plan,),
        review_queue=review_queue,
        audit_events=(audit_event,),
    )
    manifest_with_review_dict = manifest_with_review.to_dict()
    assert manifest_with_review_dict["review_queue_count"] == 1
    assert manifest_with_review_dict["audit_event_count"] == 1
    assert manifest_with_review.payload_sha256


    tree_rows = build_database_tree_rows(manifest_with_review)
    assert tree_rows[0].row_type == "database_root"
    assert any(row.row_type == "global_profiles" and row.label == "Profiles" for row in tree_rows)
    assert any(row.row_type == "case" and row.case_title == case_from_path.case_title for row in tree_rows)
    assert any(row.row_type == "articles" and row.path.replace("/", "\\").endswith(r"\Sources\Articles") for row in tree_rows)
    assert any(row.row_type == "case_profiles" and row.path.replace("/", "\\").endswith(r"\Profiles") for row in tree_rows)
    tree_text = render_database_tree_text(tree_rows)
    assert "Profiles [global_profiles]" in tree_text
    assert "Articles [articles]" in tree_text
    assert "Internal Media [internal_media]" in tree_text

    with TemporaryDirectory() as temp_root:
        temp_path = Path(temp_root)
        manifest_path = temp_path / "database_manifest.json"
        tree_path = temp_path / "database_tree.txt"
        manifest_write = write_manifest_json(manifest_with_review, manifest_path)
        assert manifest_write["status"] == "written"
        assert manifest_write["performed"] is True
        loaded_manifest = read_json_payload(manifest_path)
        assert loaded_manifest["schema_version"] == "profile-media-database-v75f"
        assert loaded_manifest["review_queue_count"] == 1
        tree_write = write_database_tree_text(manifest_with_review, tree_path)
        assert tree_write["status"] == "written"
        assert tree_write["row_count"] == len(tree_rows)
        tree_disk_text = tree_path.read_text(encoding="utf-8")
        assert "Reference Extants [reference_extants]" in tree_disk_text
        blocked_write = write_manifest_json(manifest_with_review, temp_path / "missing" / "manifest.json")
        assert blocked_write["status"] == "blocked_parent_missing"
        parent_created_write = write_manifest_json(manifest_with_review, temp_path / "created" / "manifest.json", create_parent=True)
        assert parent_created_write["status"] == "written"



if __name__ == "__main__":
    run_self_test()
    print("profile_media_database v75f OK")
