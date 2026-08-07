from __future__ import annotations

from pathlib import Path


def test_docs_describe_manual_safe_boundary() -> None:
    text = Path("SOURCE_ARCHIVE_RESULT_INTAKE.md").read_text(encoding="utf-8")
    assert "operator-supplied archive results" in text
    assert "does not fetch URLs" in text
    assert "does not validate online archive contents" in text
    assert "source_archive_review" in text


if __name__ == "__main__":
    test_docs_describe_manual_safe_boundary()
    print("Source Archive Result Intake docs self-test passed.")
