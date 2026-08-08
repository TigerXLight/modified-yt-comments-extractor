from __future__ import annotations

from pathlib import Path


def test_failure_triage_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_FAILURE_TRIAGE_RUNTIME.md").read_text(encoding="utf-8")
    assert "Failure Triage Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_FAILURE_TRIAGE_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_failure_triage_runtime_docs()
    print("Source Adapter Failure Triage Runtime docs self-test passed.")
