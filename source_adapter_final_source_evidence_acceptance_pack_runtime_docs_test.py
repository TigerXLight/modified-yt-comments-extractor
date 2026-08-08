from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_FINAL_SOURCE_EVIDENCE_ACCEPTANCE_PACK_RUNTIME.md").read_text(encoding="utf-8")
    assert "Final Source Evidence Acceptance Pack" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "final_source_evidence_acceptance_pack" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Final Source Evidence Acceptance Pack Runtime docs self-test passed.")
