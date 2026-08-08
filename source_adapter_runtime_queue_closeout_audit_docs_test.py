from __future__ import annotations

from pathlib import Path


def main() -> None:
    doc = Path("SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_AUDIT.md").read_text(encoding="utf-8")
    assert "Runtime Queue Closeout Audit" in doc
    assert "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_AUDIT_BUILT" in doc
    assert "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_COVERAGE_MATRIX_READY" in doc
    assert "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_ROADMAP_STATE_UPDATED" in doc
    assert "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_RELEASE_GATE_READY" in doc
    assert "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_READY_FOR_OPERATOR_APPROVED_NAMED_SITE_SELECTION" in doc
    assert "KEYS/ACCOUNTS" in doc
    assert "no live smoke" in doc
    assert "browser automation" in doc
    assert "network calls" in doc
    assert "API calls" in doc
    assert "archive provider submission" in doc
    assert "release upload" in doc
    assert "file-library mutation" in doc
    assert "credential storage" in doc
    assert "not GUI mutation" in doc

    audit = Path("SOURCE_EVIDENCE_ROADMAP_COVERAGE_AUDIT.md").read_text(encoding="utf-8")
    roadmap = Path("SOURCE_EVIDENCE_ROADMAP.md").read_text(encoding="utf-8")
    current = Path("CURRENT_DEV_STATE.md").read_text(encoding="utf-8")
    handoff = Path("PROJECT_CURRENT_STATE_HANDOFF.md").read_text(encoding="utf-8")
    for text in (audit, roadmap, current, handoff):
        assert "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_AUDIT_BUILT" in text
        assert "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_READY_FOR_OPERATOR_APPROVED_NAMED_SITE_SELECTION" in text
    print("Source Adapter Runtime Queue Closeout Audit docs self-test passed.")


if __name__ == "__main__":
    main()
