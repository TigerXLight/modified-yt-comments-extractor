from __future__ import annotations

from pathlib import Path

from profile_media_database import (
    CaseFolderLayout,
    CaseRecord,
    MediaBucket,
    MediaSourceRecord,
    ProfileCollectionLevel,
    ProfileMediaDatabaseManifest,
    ProfileRecord,
)
from profile_media_database_view_model import (
    ProfileMediaViewMode,
    build_profile_media_database_view_state,
    filter_database_tree_rows,
    toggle_profile_media_view_mode,
)


def _sample_manifest() -> ProfileMediaDatabaseManifest:
    root = Path("Database")
    case_root = root / "Example Case"
    layout = CaseFolderLayout(
        case_root=str(case_root),
        case_profiles_path=str(case_root / "Profiles"),
        people_path=str(case_root / "People"),
        sources_path=str(case_root / "Sources"),
        articles_path=str(case_root / "Sources" / "Articles"),
        social_media_path=str(case_root / "Sources" / "Social Media"),
        social_media_offline_path=str(case_root / "Sources" / "Social Media" / "Offline"),
        social_media_online_path=str(case_root / "Sources" / "Social Media" / "Online"),
        internal_media_path=str(case_root / "Sources" / "Internal Media"),
        reference_extants_path=str(case_root / "Reference Extants"),
    )
    global_profile = ProfileRecord(
        profile_id="profile-global-example",
        canonical_name="Example Person",
        collection_level=ProfileCollectionLevel.GLOBAL_HEADER_PROFILES,
    )
    case_profile = ProfileRecord(
        profile_id="profile-case-example",
        canonical_name="Example Person",
        collection_level=ProfileCollectionLevel.CASE_LOCAL_PROFILES,
        case_id="case-example",
    )
    media_source = MediaSourceRecord(
        source_id="source-article-example",
        source_page="Example Article",
        source_bucket=MediaBucket.ARTICLES,
        title="Example Article",
    )
    case = CaseRecord(
        case_id="case-example",
        case_title="Example Case",
        case_root=str(case_root),
        layout=layout,
        profiles=(case_profile,),
        media_sources=(media_source,),
    )
    return ProfileMediaDatabaseManifest(
        manifest_id="manifest-example",
        database_root=str(root),
        global_profiles_path=str(root / "Profiles"),
        global_profiles=(global_profile,),
        cases=(case,),
    )


def test_toggle_modes() -> None:
    assert toggle_profile_media_view_mode("FILES") == ProfileMediaViewMode.DATABASE
    assert toggle_profile_media_view_mode("database") == ProfileMediaViewMode.FILES


def test_database_view_state_has_hierarchy_and_safety_flags() -> None:
    state = build_profile_media_database_view_state(_sample_manifest(), mode="DATABASE")
    assert state.mode == ProfileMediaViewMode.DATABASE
    assert state.folder_scan_performed is False
    assert state.folder_creation_performed is False
    assert state.file_move_performed is False
    assert state.sensitive_identifier_inference_performed is False
    assert state.row_type_counts["database_root"] == 1
    assert state.row_type_counts["global_profiles"] == 1
    assert state.row_type_counts["case"] == 1
    assert state.row_type_counts["media_source"] == 1
    assert "Sources [sources]\n      Articles [articles]\n        Example Article [media_source]" in state.tree_preview
    assert "Social Media [social_media]\n        Offline [social_media_offline]\n        Online [social_media_online]" in state.tree_preview


def test_files_mode_does_not_materialize_database_rows() -> None:
    state = build_profile_media_database_view_state(_sample_manifest(), mode="FILES")
    assert state.mode == ProfileMediaViewMode.FILES
    assert state.rows == ()
    assert state.visible_rows == ()
    assert state.tree_preview == ""


def test_filter_keeps_ancestors() -> None:
    state = build_profile_media_database_view_state(_sample_manifest(), mode="DATABASE")
    filtered = filter_database_tree_rows(state.rows, "Example Article")
    labels = [row.label for row in filtered]
    assert labels == ["Database", "Example Case", "Sources", "Articles", "Example Article"]


if __name__ == "__main__":
    test_toggle_modes()
    test_database_view_state_has_hierarchy_and_safety_flags()
    test_files_mode_does_not_materialize_database_rows()
    test_filter_keeps_ancestors()
    print("profile_media_database_view_model v75h OK")
