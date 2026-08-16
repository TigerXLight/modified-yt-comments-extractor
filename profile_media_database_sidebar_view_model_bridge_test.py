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


def test_sidebar_mode_uses_view_model_only_for_mode_coercion() -> None:
    source = _main_source()
    coerce_method = _method_source(source, "_coerce_profile_media_sidebar_mode")
    assert "coerce_profile_media_view_mode" in coerce_method
    assert "build_profile_media_database_view_state" not in source
    assert "ProfileMediaDatabaseManifest" not in source
    assert "CaseFolderLayout" not in source
    assert "CaseRecord" not in source


def test_sidebar_no_longer_bridges_to_preview_manifest() -> None:
    source = _main_source()
    assert "_build_profile_media_database_sidebar_preview_manifest" not in source
    assert "_profile_media_database_sidebar_preview_text" not in source
    assert "_refresh_profile_media_database_sidebar_preview" not in source


def test_view_model_module_still_exists_for_non_sidebar_database_views() -> None:
    vm_source = Path("profile_media_database_view_model.py").read_text(encoding="utf-8")
    assert "build_profile_media_database_view_state" in vm_source
    assert "filter_database_tree_rows" in vm_source
    assert "query" in vm_source
    assert "ProfileMediaViewMode" in vm_source


if __name__ == "__main__":
    test_sidebar_mode_uses_view_model_only_for_mode_coercion()
    test_sidebar_no_longer_bridges_to_preview_manifest()
    test_view_model_module_still_exists_for_non_sidebar_database_views()
    print("profile_media_database_sidebar_view_model_bridge_mode_only v75l OK")
