from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_RELEASE_FILE_LIBRARY_FINALIZER_RUNTIME.md").read_text(encoding="utf-8")
    assert "Release File Library Finalizer" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "release_file_library_finalizer" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Release File Library Finalizer Runtime docs self-test passed.")
