from pathlib import Path


def test_archive_handoff_docs_cover_operator_gate():
    doc = Path("CAPTURE_MSN_MANUAL_ARCHIVE_HANDOFF.md").read_text(encoding="utf-8")
    assert "external-archive handoff boundary" in doc
    assert "manual-only archive tasks" in doc
    assert "does not fetch live pages" in doc
    assert "does not" in doc and "submit archive requests" in doc


def test_archive_handoff_module_declares_next_boundary():
    text = Path("capture_msn_manual_archive_handoff.py").read_text(encoding="utf-8")
    assert "msn_manual_archive_handoff_v1" in text
    assert "msn_manual_archive_result_intake" in text
    assert "MANUAL_OPERATOR_ONLY" in text
    assert "external_call_performed_by_code" in text


if __name__ == "__main__":
    test_archive_handoff_docs_cover_operator_gate()
    test_archive_handoff_module_declares_next_boundary()
    print("MSN manual archive handoff docs self-test passed.")
