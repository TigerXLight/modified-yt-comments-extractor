from pathlib import Path


def test_archive_result_intake_docs_cover_boundaries():
    text = Path("CAPTURE_MSN_MANUAL_ARCHIVE_RESULT_INTAKE.md").read_text(encoding="utf-8")
    assert "archive-result intake" in text
    assert "operator-supplied archive result JSON" in text
    assert "does not fetch pages" in text
    assert "does not" in text


if __name__ == "__main__":
    test_archive_result_intake_docs_cover_boundaries()
    print("MSN manual archive result intake docs self-test passed.")
