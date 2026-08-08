from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_EVIDENCE_QUEUE_RELEASE_DISPATCH_RUNTIME.md").read_text(encoding="utf-8")
    assert "Evidence Queue Release Dispatch" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "evidence_queue_release_dispatch" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Evidence Queue Release Dispatch Runtime docs self-test passed.")
