from capture_dependency_audit import (
    DEPENDENCY_AUDIT_SCOPE,
    DEPENDENCY_DECISION_EXTERNAL_ONLY,
    DEPENDENCY_DECISION_REFERENCE,
    DEPENDENCY_DECISION_SELECT,
    DEPENDENCY_DECISION_USER_CONFIGURED_EXTERNAL,
    available_capture_dependency_audit_items,
    capture_dependency_audit_to_dict,
    dependency_audit_item_by_name,
)


def test_dependency_audit_includes_rev4_candidates_without_installing() -> None:
    names = {item.name for item in available_capture_dependency_audit_items()}

    assert "playwright" in names
    assert "trafilatura" in names
    assert "warcio" in names
    assert "ffmpeg" in names
    assert "ArchiveBox" in names
    assert "Video DownloadHelper installed extension" in names

    playwright = dependency_audit_item_by_name("playwright")
    assert playwright is not None
    assert playwright.decision == DEPENDENCY_DECISION_SELECT
    assert playwright.optional is True
    assert playwright.auto_install is False


def test_external_and_reference_items_are_not_auto_installed() -> None:
    ffmpeg = dependency_audit_item_by_name("ffmpeg")
    helper = dependency_audit_item_by_name("Video DownloadHelper installed extension")
    archive_web = dependency_audit_item_by_name("ArchiveWeb.page")

    assert ffmpeg is not None
    assert ffmpeg.decision == DEPENDENCY_DECISION_USER_CONFIGURED_EXTERNAL
    assert ffmpeg.auto_install is False

    assert helper is not None
    assert helper.decision == DEPENDENCY_DECISION_REFERENCE
    assert helper.auto_install is False
    assert "do not copy" in helper.notes

    assert archive_web is not None
    assert archive_web.decision == DEPENDENCY_DECISION_EXTERNAL_ONLY
    assert archive_web.auto_install is False


def test_dependency_audit_to_dict_is_primitive_and_local_only() -> None:
    data = capture_dependency_audit_to_dict()

    assert data["scope"] == DEPENDENCY_AUDIT_SCOPE
    assert "no install" in data["scope"]
    assert data["dependency_count"] == len(data["dependencies"])
    assert all(isinstance(item, dict) for item in data["dependencies"])
    assert "pip install" not in repr(data)
    assert "playwright install" not in repr(data)
    assert "requests.get" not in repr(data)


def run_self_test() -> None:
    test_dependency_audit_includes_rev4_candidates_without_installing()
    test_external_and_reference_items_are_not_auto_installed()
    test_dependency_audit_to_dict_is_primitive_and_local_only()


if __name__ == "__main__":
    run_self_test()
    print("Capture dependency audit self-test passed.")
