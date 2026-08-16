from pathlib import Path


def _main_source() -> str:
    return Path("main.py").read_text(encoding="utf-8")


def _method_source(source: str, method_name: str) -> str:
    anchor = f"    def {method_name}"
    start = source.index(anchor)
    next_start = source.find("\n    def ", start + len(anchor))
    if next_start == -1:
        return source[start:]
    return source[start:next_start]


def test_sidebar_preview_bridges_to_profile_media_database_view_model() -> None:
    source = _main_source()
    preview_method = _method_source(source, "_profile_media_database_sidebar_preview_text")
    manifest_method = _method_source(source, "_build_profile_media_database_sidebar_preview_manifest")

    assert "build_profile_media_database_view_state" in preview_method
    assert "ProfileMediaDatabaseManifest" in manifest_method
    assert "CaseFolderLayout" in manifest_method
    assert "CaseRecord" in manifest_method
    assert "global_profiles_path=str(database_root / \"Profiles\")" in manifest_method
    assert "case_profiles_path=str(case_root / \"Profiles\")" in manifest_method


def test_sidebar_preview_keeps_sources_subtree_inside_case_manifest() -> None:
    source = _main_source()
    manifest_method = _method_source(source, "_build_profile_media_database_sidebar_preview_manifest")

    assert 'sources_path=str(case_root / "Sources")' in manifest_method
    assert 'articles_path=str(case_root / "Sources" / "Articles")' in manifest_method
    assert 'social_media_path=str(case_root / "Sources" / "Social Media")' in manifest_method
    assert 'social_media_offline_path=str(case_root / "Sources" / "Social Media" / "Offline")' in manifest_method
    assert 'social_media_online_path=str(case_root / "Sources" / "Social Media" / "Online")' in manifest_method
    assert 'internal_media_path=str(case_root / "Sources" / "Internal Media")' in manifest_method
    assert 'reference_extants_path=str(case_root / "Reference Extants")' in manifest_method


def test_sidebar_preview_bridge_has_no_real_filesystem_action() -> None:
    source = _main_source()
    combined = "\n".join(
        (
            _method_source(source, "_build_profile_media_database_sidebar_preview_manifest"),
            _method_source(source, "_profile_media_database_sidebar_preview_text"),
        )
    ).lower()

    forbidden = (
        ".mkdir(",
        "os.mkdir",
        "rmdir(",
        "os.rename",
        "os.replace",
        "shutil.move",
        "copyfile(",
        "copytree(",
        "unlink(",
        "os.walk",
        "rglob(",
        "glob(",
        "classify(",
    )
    for term in forbidden:
        assert term not in combined


if __name__ == "__main__":
    test_sidebar_preview_bridges_to_profile_media_database_view_model()
    test_sidebar_preview_keeps_sources_subtree_inside_case_manifest()
    test_sidebar_preview_bridge_has_no_real_filesystem_action()
    print("profile_media_database_sidebar_view_model_bridge v75k OK")
