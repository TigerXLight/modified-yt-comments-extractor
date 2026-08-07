from pathlib import Path


def test_archive_review_package_docs_cover_boundaries():
    text = Path("CAPTURE_MSN_MANUAL_ARCHIVE_REVIEW_PACKAGE.md").read_text(encoding="utf-8")
    assert "archive-review package" in text
    assert "msn_manual_archive_result_intake_v1" in text
    assert "does not fetch archived URLs" in text
    assert "does not" in text


if __name__ == "__main__":
    test_archive_review_package_docs_cover_boundaries()
    print("MSN manual archive review package docs self-test passed.")
