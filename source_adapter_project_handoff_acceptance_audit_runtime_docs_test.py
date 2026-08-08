from pathlib import Path


def test_docs_cover_operator_and_redaction_boundaries():
    text = Path("SOURCE_ADAPTER_PROJECT_HANDOFF_ACCEPTANCE_AUDIT_RUNTIME.md").read_text(encoding="utf-8")
    assert "Project Handoff Acceptance Audit" in text
    assert "operator-approved" in text
    assert "Credential" in text or "credential" in text
    assert "redacted" in text
    assert "project_handoff_acceptance_audit" in text


if __name__ == "__main__":
    test_docs_cover_operator_and_redaction_boundaries()
    print("Source Adapter Project Handoff Acceptance Audit Runtime docs self-test passed.")
