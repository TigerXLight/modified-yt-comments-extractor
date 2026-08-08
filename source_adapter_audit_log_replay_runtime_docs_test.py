from __future__ import annotations

from pathlib import Path


def test_audit_log_replay_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_AUDIT_LOG_REPLAY_RUNTIME.md").read_text(encoding="utf-8")
    assert "Audit Log Replay Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_AUDIT_LOG_REPLAY_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_audit_log_replay_runtime_docs()
    print("Source Adapter Audit Log Replay Runtime docs self-test passed.")
