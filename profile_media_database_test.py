from profile_media_database import (
    ClaimBasis,
    CurrentnessStatus,
    MediaBucket,
    MovePlanStatus,
    ProfileCollectionLevel,
    ProfileSourceRole,
    build_case_folder_layout,
    build_case_record,
    build_global_profiles_path,
    build_manifest,
    build_media_source_record,
    build_profile_record,
    parse_profile_text_blocks,
    plan_folder_move,
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
    assert manifest_dict["schema_version"] == "profile-media-database-v75a"
    assert manifest_dict["case_count"] == 1
    assert manifest_dict["global_profile_count"] == 1
    assert manifest.payload_sha256

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


if __name__ == "__main__":
    run_self_test()
    print("profile_media_database v75a OK")
