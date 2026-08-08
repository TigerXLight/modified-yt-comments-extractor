from __future__ import annotations

from pathlib import Path


def test_runtime_operator_acceptance_closeout_docs() -> None:
    text = Path("SOURCE_ADAPTER_RUNTIME_OPERATOR_ACCEPTANCE_CLOSEOUT.md").read_text(encoding="utf-8")
    assert "Runtime Operator Acceptance Closeout" in text
    assert "KEYS/ACCOUNTS" in text
    assert "operator_approved_live" in text
    assert "manual/live smoke" in text
    assert "source_adapter_runtime_operator_acceptance_closeout_v1" in text


if __name__ == "__main__":
    test_runtime_operator_acceptance_closeout_docs()
    print("Source Adapter Runtime Operator Acceptance Closeout docs self-test passed.")
